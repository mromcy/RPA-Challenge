"""
Comparação medida entre os drivers Playwright e Selenium.

Execução manual, fora do CI e fora do pytest:

    poetry run task benchmark
    poetry run python -m benchmarks.compare_drivers --repeticoes 5

Regras de método, todas deliberadas:

- **Mesmo binário nos dois lados.** O script se recusa a rodar sem PATH_BROWSER
  preenchido: o Playwright dirigiria o Chromium dele e o Selenium o Chrome do
  sistema, e a diferença medida seria em parte navegador contra navegador.
- **Aquecimento descartado.** A primeira execução de cada driver paga DNS, cache
  de disco frio e primeira conexão — custo de estrear, não de rodar.
- **Medições intercaladas**, e não em blocos. Se a rede piorar no meio da
  execução, blocos jogariam a culpa em quem rodasse depois. Alternando, qualquer
  variação do ambiente se distribui entre os dois.
- **Mediana**, com mínimo e máximo ao lado. Média deixa um pico do antivírus
  contaminar o resultado; mediana não.
- **Falha interrompe.** Nenhuma execução é repetida em silêncio nem substituída
  por outro valor — benchmark que esconde falha é propaganda.
"""

from __future__ import annotations

import argparse
import ast
import io
import platform
import re
import statistics
import time
import tokenize
from datetime import date
from pathlib import Path

from resources.Drivers.playwright_driver import PlaywrightDriver
from resources.Drivers.selenium_driver import SeleniumDriver
from resources.Modules.challenge import CAMPOS_DO_FORMULARIO, Challenge
from resources.Schemas.item_run import Item
from resources.settings import get_settings
from resources.Utils.ler_arquivo import LerArquivo

RAIZ = Path(__file__).resolve().parents[1]
URL = 'https://rpachallenge.com/'

CONSTRUTORES = {'playwright': PlaywrightDriver, 'selenium': SeleniumDriver}

ARQUIVOS_DE_DRIVER = {
    'playwright': RAIZ / 'resources' / 'Drivers' / 'playwright_driver.py',
    'selenium': RAIZ / 'resources' / 'Drivers' / 'selenium_driver.py',
}

PADRAO_TEMPO_DO_SITE = re.compile(r'in (\d+) milliseconds')
PADRAO_SUCESSO = re.compile(r'(\d+)%')


class _SemLog:
    """
    Logger nulo.

    O Challenge registra uma linha por formulário; com 12 execuções isso seriam
    centenas de linhas competindo com a tabela de resultados na saída.
    """

    def info(self, *_, **__) -> None: ...

    def warning(self, *_, **__) -> None: ...

    def error(self, *_, **__) -> None: ...


def versao_do_navegador(caminho: str) -> str:
    """
    Descobre a versão do Chrome apontado por PATH_BROWSER.

    Lê o nome da pasta irmã versionada, criada pelo instalador do Chrome
    (``Application/150.0.7871.187/``). Deliberadamente **não** executa
    ``chrome.exe --version``: no Windows isso não imprime versão nenhuma — abre
    uma janela do navegador, o que é efeito colateral inaceitável num script
    de medição.
    """
    pasta = Path(caminho).parent
    versoes = [
        sub.name
        for sub in pasta.iterdir()
        if sub.is_dir() and re.match(r'^\d+\.\d+', sub.name)
    ]

    return max(versoes, default='desconhecida')


def carregar_itens() -> list[Item]:
    """Os registros de Entrada/, pelo mesmo caminho que a produção percorre."""
    dados = LerArquivo(_SemLog(), path_in=RAIZ / 'Entrada').ler_arquivo()

    return [
        Item(
            id=numero,
            item_id=numero,
            **{
                atributo: str(linha[rotulo])
                for rotulo, atributo in CAMPOS_DO_FORMULARIO.items()
            },
        )
        for numero, (_, linha) in enumerate(dados.iterrows(), 1)
    ]


def uma_execucao(nome: str, itens: list[Item], path_browser: str) -> dict[str, float]:
    """
    Roda o desafio completo uma vez e devolve os tempos, em segundos.

    Returns:
        dict: `total` cronometrado por nós, do zero até o resultado lido, e
            `fill` lido da mensagem do próprio site — medição independente,
            imune a onde colocamos o cronômetro.

    Raises:
        RuntimeError: Se o desafio não fechar em 100% ou se o site não informar
            o tempo. Resultado parcial não é medição válida.
    """
    driver = CONSTRUTORES[nome](headless=True, path_browser=path_browser)
    challenge = Challenge(driver, _SemLog())

    try:
        inicio = time.perf_counter()

        challenge.iniciar_desafio(URL)
        for item in itens:
            challenge.preencher_formulario(item)
        resultado = challenge.capturar_resultado()

        total = time.perf_counter() - inicio
    finally:
        driver.fechar()

    sucesso = PADRAO_SUCESSO.search(resultado)
    if not sucesso or sucesso.group(1) != '100':
        raise RuntimeError(f'{nome}: desafio não fechou em 100% — {resultado!r}')

    tempo = PADRAO_TEMPO_DO_SITE.search(resultado)
    if not tempo:
        raise RuntimeError(f'{nome}: o site não informou o tempo — {resultado!r}')

    return {'total': total, 'fill': int(tempo.group(1)) / 1000}


def medir_arquivo(caminho: Path) -> dict[str, int]:
    """
    Tamanho de um módulo em três contagens (decisão 14 do progresso).

    `stmts` são instruções executáveis da árvore sintática e medem quanto o
    programa faz. `efetivas` são linhas físicas sem docstrings, comentários e
    linhas vazias, e medem quanto se lê — a diferença entre as duas aparece
    quando uma instrução ocupa várias linhas. `linhas` cruas entram só por
    transparência: elas medem densidade de documentação do autor, não exigência
    da biblioteca.
    """
    texto = caminho.read_text(encoding='utf-8')
    arvore = ast.parse(texto)

    ignoradas: set[int] = set()
    for no in ast.walk(arvore):
        if (
            isinstance(no, ast.Expr)
            and isinstance(no.value, ast.Constant)
            and isinstance(no.value.value, str)
        ):
            ignoradas.update(range(no.lineno, (no.end_lineno or no.lineno) + 1))

    for token in tokenize.generate_tokens(io.StringIO(texto).readline):
        if token.type == tokenize.COMMENT and token.line.strip().startswith('#'):
            ignoradas.add(token.start[0])

    linhas = texto.splitlines()
    efetivas = [
        numero
        for numero, conteudo in enumerate(linhas, 1)
        if conteudo.strip() and numero not in ignoradas
    ]

    return {
        'linhas': len(linhas),
        'efetivas': len(efetivas),
        'stmts': sum(
            1
            for no in ast.walk(arvore)
            if isinstance(no, ast.stmt)
            and not (isinstance(no, ast.Expr) and isinstance(no.value, ast.Constant))
        ),
        'esperas': texto.count('wait_for(') + texto.count('self._esperar('),
        'sleeps': texto.count('time.sleep'),
    }


def _resumo(valores: list[float]) -> str:
    """Mediana com mínimo e máximo entre parênteses, em segundos."""
    return f'**{statistics.median(valores):.2f}** ({min(valores):.2f}–{max(valores):.2f})'


def imprimir_resultados(
    medicoes: dict[str, list[dict[str, float]]],
    repeticoes: int,
    versao: str,
) -> None:
    """Imprime as duas tabelas em markdown, prontas para colar no README."""
    print('\n### Tempo de execução\n')
    print('| Driver | total (s) | fill (s) | resto (s) |')
    print('|---|---|---|---|')

    for nome, execucoes in medicoes.items():
        totais = [e['total'] for e in execucoes]
        fills = [e['fill'] for e in execucoes]
        restos = [e['total'] - e['fill'] for e in execucoes]
        print(f'| {nome} | {_resumo(totais)} | {_resumo(fills)} | {_resumo(restos)} |')

    print(
        '\nMediana de '
        f'{repeticoes} execuções, com mínimo e máximo entre parênteses. '
        '`total` é cronometrado aqui, de ponta a ponta, incluindo subir o '
        'navegador. `fill` é reportado pelo próprio rpachallenge.com. `resto` é '
        'a subtração dos dois: subida do navegador, clique no Start e leitura '
        'do resultado — **não** é só o startup, e por isso não recebe esse nome.'
    )

    print('\n### Complexidade do código\n')
    print('| Driver | statements | linhas efetivas | esperas explícitas | time.sleep |')
    print('|---|---|---|---|---|')

    for nome, caminho in ARQUIVOS_DE_DRIVER.items():
        m = medir_arquivo(caminho)
        print(
            f'| {nome} | {m["stmts"]} | {m["efetivas"]} | '
            f'{m["esperas"]} | {m["sleeps"]} |'
        )

    print(
        '\nSó os módulos de driver entram na conta: `base.py` e `seletores.py` '
        'são compartilhados e não pertencem a nenhum dos lados. `statements` '
        'ignora docstrings; `linhas efetivas` desconta docstrings, comentários '
        'e linhas vazias.'
    )

    print('\n### Metodologia\n')
    print(f'- Máquina: {platform.processor() or "desconhecida"}')
    print(f'- Sistema: {platform.system()} {platform.release()}')
    print(f'- Python: {platform.python_version()}')
    print(f'- Navegador: Chrome {versao}, o mesmo para os dois drivers')
    print(f'- Execuções medidas: {repeticoes} por driver, headless')
    print('- Primeira execução de cada driver descartada como aquecimento')
    print('- Medições intercaladas entre os drivers, não em blocos')
    print(f'- Data: {date.today().isoformat()}')


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='compare_drivers',
        description='Mede Playwright contra Selenium no mesmo fluxo.',
    )
    parser.add_argument(
        '--repeticoes',
        type=int,
        default=5,
        help='Execuções medidas por driver, sem contar o aquecimento.',
    )
    argumentos = parser.parse_args()

    path_browser = get_settings().PATH_BROWSER
    if not path_browser:
        raise SystemExit(
            'PATH_BROWSER está vazio no config.json.\n'
            'O benchmark exige que os dois drivers dirijam o MESMO executável: '
            'sem isso, o Playwright usaria o Chromium que ele gerencia e o '
            'Selenium usaria o Chrome do sistema, e parte da diferença medida '
            'seria navegador contra navegador, não biblioteca contra biblioteca.'
        )

    versao = versao_do_navegador(path_browser)
    itens = carregar_itens()

    print(f'Navegador: Chrome {versao}')
    print(f'Registros por execução: {len(itens)}')
    print('\nAquecimento (descartado)...')
    for nome in CONSTRUTORES:
        uma_execucao(nome, itens, path_browser)
        print(f'  {nome}: ok')

    medicoes: dict[str, list[dict[str, float]]] = {nome: [] for nome in CONSTRUTORES}

    print(f'\nMedindo {argumentos.repeticoes} execuções por driver, intercaladas...')
    for rodada in range(1, argumentos.repeticoes + 1):
        for nome in CONSTRUTORES:
            tempos = uma_execucao(nome, itens, path_browser)
            medicoes[nome].append(tempos)
            print(
                f'  rodada {rodada} · {nome:<10} '
                f'total={tempos["total"]:6.2f}s  fill={tempos["fill"]:5.2f}s'
            )

    imprimir_resultados(medicoes, argumentos.repeticoes, versao)


if __name__ == '__main__':
    main()
