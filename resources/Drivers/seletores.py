"""
Seletores da página do RPA Challenge, independentes de biblioteca.

Ficam num módulo próprio, e não dentro de cada driver, porque descrevem o
**site** e não a **ferramenta**: os dois drivers atacam a mesma página. Se cada
um carregasse sua cópia, uma mudança no DOM teria de ser corrigida em dois
lugares — e a afirmação de que ambos usam a mesma estratégia de localização
passaria a depender de disciplina, em vez de ser verificável.

Isso importa para o benchmark: com as mesmas strings dos dois lados, a diferença
de tempo medida não pode ser atribuída a um driver ter recebido seletor melhor
que o outro.

Todos são semânticos — por rótulo ou por texto visível. Nenhum XPath absoluto
nem índice posicional, que quebram ao menor rearranjo da página.
"""

XPATH_CAMPO_POR_ROTULO = "//label[text()='{rotulo}']/following-sibling::input"
"""
Campo de entrada irmão do rótulo visível. Formatar com o nome do campo.

Localizar por rótulo é obrigatório, não preferência: o desafio **embaralha a
ordem dos campos a cada rodada**. Qualquer seletor posicional preencheria o
campo errado — que é precisamente a armadilha que o site propõe.
"""

XPATH_BOTAO_INICIAR = "//button[text()='Start']"
"""<button ...>Start</button>"""

XPATH_BOTAO_ENVIAR = "//input[@type='submit' and @value='Submit']"
"""
<input type="submit" value="Submit"> — **não** é um <button>.

A assimetria entre os dois botões é real e vale saber: o código anterior usava
`get_by_role('button', name='Submit')` e funcionava, porque o motor de
acessibilidade do Playwright atribui papel de botão a um input[type=submit] e
tira o nome do atributo `value`. O Selenium não tem essa abstração. Escrever o
seletor explícito é o que permite os dois drivers usarem a mesma string — e
evita atribuir ao Selenium uma dificuldade que era só falta de açúcar sintático.
"""

XPATH_RESULTADO = "//*[contains(text(),'Your success rate')]"
"""
Mensagem final do desafio, algo como
'Your success rate is 100% (70 out of 70 fields) in 807 milliseconds'.

O tempo de preenchimento que o benchmark usa sai daqui — é medição feita pelo
próprio site, independente do nosso cronômetro.
"""
