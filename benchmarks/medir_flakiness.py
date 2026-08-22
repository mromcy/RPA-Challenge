"""
Mede instabilidade (flakiness) da suíte E2E em cada driver.

Um teste instável passa e falha **sem que o código mude**: o resultado deixa de
ser função do código e passa a depender de tempo de resposta, renderização e
carga da máquina. É a pior categoria de defeito porque não se reproduz sob
investigação — e porque o time aprende a reagir a vermelho com "roda de novo",
até o dia em que o vermelho é verdadeiro.

Em RPA a mesma causa produz robô intermitente em produção. Robô lento é
incômodo que se resolve agendando mais cedo; robô intermitente consome uma
investigação por semana e mina a confiança de quem depende dele.

O método é rodar o **teste E2E de verdade**, um processo por execução, e contar
saídas diferentes de zero. Reimplementar o fluxo aqui mediria outra coisa.

**O que este número NÃO prova**, e o relatório repete isso na saída:

1. Zero falhas não é zero instabilidade. Pela regra dos três, nenhuma ocorrência
   em N tentativas dá um limite superior de ~3/N com 95% de confiança — com 10
   execuções, isso é 30%. Para afirmar "menos de 1%" seriam ~300 execuções.
2. Isto mede **as implementações**, não as bibliotecas. Um driver Selenium com
   time.sleep e XPath absoluto seria escandalosamente instável; o nosso tem
   WebDriverWait em toda interação de propósito. Zero nos dois lados é o
   resultado **desejado**: confirma que a robustez é comparável e que a
   diferença medida no benchmark é de velocidade, não de confiabilidade.

    poetry run python -m benchmarks.medir_flakiness --repeticoes 10
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

DRIVERS = ('playwright', 'selenium')
NO_DE_TESTE = (
    'tests/test_e2e_challenge.py::test_desafio_completo_com_sucesso_total[{driver}]'
)


def uma_rodada(driver: str) -> tuple[bool, str]:
    """
    Roda o teste E2E daquele driver num processo limpo.

    Returns:
        tuple[bool, str]: Se passou, e a saída do pytest para diagnóstico.
    """
    resultado = subprocess.run(
        [
            sys.executable,
            '-m',
            'pytest',
            NO_DE_TESTE.format(driver=driver),
            '-q',
            '--no-header',
            '-p',
            'no:cacheprovider',
        ],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )

    return resultado.returncode == 0, resultado.stdout


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='medir_flakiness',
        description='Conta falhas da suíte E2E em execuções repetidas.',
    )
    parser.add_argument('--repeticoes', type=int, default=10)
    argumentos = parser.parse_args()

    falhas: dict[str, list[str]] = {driver: [] for driver in DRIVERS}

    print(f'Rodando a suíte E2E {argumentos.repeticoes}× por driver.\n')

    for rodada in range(1, argumentos.repeticoes + 1):
        for driver in DRIVERS:
            passou, saida = uma_rodada(driver)
            if not passou:
                falhas[driver].append(saida)
            print(f'  rodada {rodada:>2} · {driver:<10} {"ok" if passou else "FALHOU"}')

    print('\n### Instabilidade\n')
    print('| Driver | execuções | falhas | taxa observada |')
    print('|---|---|---|---|')

    for driver in DRIVERS:
        quantidade = len(falhas[driver])
        taxa = quantidade / argumentos.repeticoes
        print(f'| {driver} | {argumentos.repeticoes} | {quantidade} | {taxa:.0%} |')

    # A regra dos três é uma aproximação; abaixo de ~3 execuções ela devolveria
    # um limite maior que 100%, que não quer dizer nada.
    limite = min(3 / argumentos.repeticoes, 1.0)
    print(
        f'\nZero falhas em {argumentos.repeticoes} execuções **não** significa zero '
        f'instabilidade: pela regra dos três, o limite superior com 95% de confiança '
        f'é de aproximadamente {limite:.0%}. Esta medição detecta problema grosseiro; '
        'não certifica confiabilidade. Ela também mede as implementações deste '
        'repositório, não as bibliotecas em geral.'
    )

    for driver, saidas in falhas.items():
        for numero, saida in enumerate(saidas, 1):
            print(f'\n--- falha {numero} em {driver} ---')
            print(saida.strip()[-1500:])


if __name__ == '__main__':
    main()
