# RPA Challenge Bot

Bot de automação RPA desenvolvido em Python para resolver o [RPA Challenge](https://rpachallenge.com/). O bot lê dados de um arquivo Excel, persiste o estado da execução em um banco PostgreSQL e preenche formulários automaticamente no navegador usando Playwright.

---

## Objetivo

O [RPA Challenge](https://rpachallenge.com/) é um desafio de automação que exige:

1. Ler uma planilha Excel com dados de pessoas
2. Acessar o site e clicar em **Start**
3. Preencher um formulário com 7 campos para cada registro
4. Submeter o formulário repetidamente (os campos reposicionam a cada submissão)
5. Capturar a taxa de sucesso final exibida pelo site

Este projeto implementa essa automação de forma **enterprise-ready**, com rastreabilidade completa por banco de dados, logging multi-destino e tratamento robusto de erros.

---

## Como funciona

```
Excel (Entrada/) → Banco de Dados → Browser (Playwright) → Resultado
      ↓                  ↓                   ↓                  ↓
  Leitura dos        Persistência        Preenchimento       Taxa de
  dados de entrada   de estado e         automático do       sucesso
                     auditoria           formulário          registrada
```

---

## Arquitetura

```
RPA_CHALLENGE/
├── bot.py                          # Ponto de entrada da aplicação
├── config.json                     # Arquivo de configuração principal
├── alembic.ini                     # Configuração do Alembic (migrations)
├── Entrada/                        # Coloque aqui os arquivos Excel de entrada
├── Saida/                          # Diretório para arquivos de saída
├── logs/                           # Logs gerados automaticamente (diários)
├── downloads/                      # Downloads do browser (gerado automaticamente)
├── secret/                         # Credenciais criptografadas (gerado automaticamente)
│   └── db_credentials/
│       ├── credentials.json        # Usuário e senha criptografados com Fernet
│       └── secret.key              # Chave de criptografia Fernet
├── migrations/                     # Histórico de migrations Alembic
│   ├── env.py
│   └── versions/
│       ├── 3da4bd0b1cc6_create_item_run_and_item_tables.py
│       └── 85e9772f5731_add_colum_result_in_item_table.py
└── resources/
    ├── settings.py                 # Carregamento de config via Pydantic + criptografia
    ├── database.py                 # Engine SQLAlchemy e gerenciamento de sessão
    ├── models.py                   # ORM models e enums de status
    ├── execute.py                  # Orquestrador principal
    ├── Executers/
    │   └── execute_challenge.py    # Fluxo de execução do challenge
    ├── Modules/
    │   ├── challenge.py            # Classe com interações do browser
    │   └── locators.py             # Seletores CSS/XPath dos elementos do site
    ├── Schemas/
    │   ├── item_run.py             # Schemas Pydantic: ItemRun, Item, ItemInfo
    │   └── process_run.py          # Schema Pydantic: ProcessRun
    ├── Tools/
    │   ├── add_process_run.py      # Cria o registro inicial de execução no banco
    │   └── logs.py                 # Sistema de logging multi-destino
    └── Utils/
        ├── create_items.py         # Persiste itens do DataFrame no banco
        ├── ler_arquivo.py          # Leitura e limpeza de arquivos Excel
        └── operation_db.py         # Operações CRUD no banco de dados
```

---

## Pré-requisitos

- **Python** >= 3.11, < 3.14
- **PostgreSQL** >= 13 (rodando localmente ou acessível na rede)
- **Google Chrome** instalado
- **Git** para clonar o repositório

---

## Instalação

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd RPA_CHALLENGE
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat

# Linux/macOS
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -e .
```

> Se o projeto usar `requirements.txt` ao invés de `pyproject.toml`:
> ```bash
> pip install -r requirements.txt
> ```

### 4. Instale os browsers do Playwright

```bash
playwright install chromium
```

---

## Configuração

### `config.json`

Edite o arquivo `config.json` na raiz do projeto com os valores do seu ambiente:

```json
{
    "PROJECT_NAME": "rpa_challenge",
    "AREA": "Hiperautomação",
    "PATH_BASE": "<caminho absoluto para a raiz do projeto>",
    "PATH_URL": "https://rpachallenge.com/",
    "PATH_IN": "<caminho absoluto para a pasta Entrada>",
    "PATH_OUT": "<caminho absoluto para a pasta Saida>",
    "PATH_DRIVER": "<caminho absoluto para o executável do Chrome>",
    "HOST_DB_POSTGRES": "localhost",
    "PORT_DB_POSTGRES": 5432,
    "DB_NAME_POSTGRES": "<nome_do_banco>",
    "DB_SCHEMA": "rpa_challenge"
}
```

| Campo | Descrição |
|-------|-----------|
| `PROJECT_NAME` | Identificador do processo no banco de dados |
| `AREA` | Área responsável pelo processo |
| `PATH_BASE` | Diretório raiz do projeto |
| `PATH_URL` | URL do site alvo |
| `PATH_IN` | Pasta onde ficam os arquivos Excel de entrada |
| `PATH_OUT` | Pasta para arquivos de saída |
| `PATH_DRIVER` | Caminho do executável do Google Chrome |
| `HOST_DB_POSTGRES` | Host do PostgreSQL |
| `PORT_DB_POSTGRES` | Porta do PostgreSQL (padrão: 5432) |
| `DB_NAME_POSTGRES` | Nome do banco de dados |
| `DB_SCHEMA` | Schema do projeto no banco |

> **Nota:** Os diretórios `logs/`, `downloads/` e `secret/` são criados automaticamente na primeira execução.

---

### Credenciais do banco de dados (criptografadas)

As credenciais de acesso ao PostgreSQL são armazenadas criptografadas com [Fernet](https://cryptography.io/en/latest/fernet/) na pasta `secret/db_credentials/`.

**Estrutura esperada:**

```
secret/
└── db_credentials/
    ├── credentials.json   ← {"email": "<usuario_criptografado>", "password": "<senha_criptografada>"}
    └── secret.key         ← chave Fernet gerada (binário)
```

**Como gerar as credenciais:**

```python
from cryptography.fernet import Fernet
import json, os

# Gerar chave
key = Fernet.generate_key()
fernet = Fernet(key)

# Criptografar credenciais
usuario = fernet.encrypt(b"seu_usuario").decode()
senha   = fernet.encrypt(b"sua_senha").decode()

# Salvar arquivos
os.makedirs("secret/db_credentials", exist_ok=True)

with open("secret/db_credentials/secret.key", "wb") as f:
    f.write(key)

with open("secret/db_credentials/credentials.json", "w") as f:
    json.dump({"email": usuario, "password": senha}, f)
```

---

## Banco de dados e Migrations

### 1. Crie o banco e o schema no PostgreSQL

```sql
CREATE DATABASE <nome_do_banco>;
\c <nome_do_banco>
CREATE SCHEMA IF NOT EXISTS rpa_challenge;
CREATE SCHEMA IF NOT EXISTS process_manager;
```

### 2. Execute as migrations com Alembic

```bash
alembic upgrade head
```

Isso criará automaticamente as tabelas:
- `rpa_challenge.item_run` — rastreamento individual de cada item processado
- `rpa_challenge.item` — dados do formulário + resultado

> A tabela `process_manager.process_run` deve existir previamente (gerenciada externamente) ou ser criada via migration adicional.

---

## Arquivo de entrada (Excel)

Coloque um arquivo `.xlsx` na pasta `Entrada/` com as seguintes colunas (os nomes devem ser exatamente esses):

| Coluna | Descrição |
|--------|-----------|
| `First Name` | Primeiro nome |
| `Last Name` | Sobrenome |
| `Company Name` | Nome da empresa |
| `Role in Company` | Cargo |
| `Address` | Endereço |
| `Email` | E-mail |
| `Phone Number` | Telefone |

> O bot lê automaticamente todos os `.xlsx` encontrados na pasta, em ordem de modificação (mais recente primeiro).

---

## Execução

```bash
python bot.py
```

---

## Fluxo detalhado de execução

```
bot.py
  └── Execute().execute()
        │
        ├── 1. AddProcessRun().execute()
        │      Cria registro process_run com status SCHEDULED
        │      Retorna run_id
        │
        ├── 2. update_process_run_status(RUNNING)
        │
        ├── 3. LerArquivo().ler_arquivo()
        │      Lê Excel da pasta Entrada/
        │      Limpa colunas e linhas vazias
        │      Retorna DataFrame
        │
        ├── 4. create_items(df, run_id)
        │      Para cada linha do DataFrame:
        │        ├── Cria ORMItemRun (status: QUEUED)
        │        └── Cria ORMItem com os dados do formulário
        │
        ├── 5. get_queued_items_by_run(run_id)
        │      Busca todos os itens com status QUEUED
        │
        ├── 6. ExecuteChallenge().execute(items)
        │      Abre Chrome com Playwright
        │      Acessa rpachallenge.com
        │      Clica em "Start"
        │      Para cada item:
        │        ├── update_item_run_status(PROCESSING)
        │        ├── Preenche os 7 campos do formulário
        │        ├── Clica em "Submit"
        │        └── update_item_run_status(COMPLETED)
        │      Captura taxa de sucesso final
        │      Fecha o browser
        │
        ├── 7. update_items_result(item_ids, resultado)
        │      Salva a taxa de sucesso em todos os itens
        │
        └── 8. update_process_run_status(COMPLETED)
               Em caso de erro: update_process_run_status(FAILED)
               com error_message e error_stack
```

---

## Modelos de dados

### `process_run` (schema: `process_manager`)

Rastreia o ciclo de vida completo de uma execução do bot.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `run_id` | INT (PK) | Identificador único da execução |
| `process_name` | VARCHAR | Nome do processo |
| `resource_name` | VARCHAR | Hostname da máquina que executou |
| `scheduled_by` | VARCHAR | Usuário que iniciou |
| `area` | VARCHAR | Área responsável |
| `status` | ENUM | `SCHEDULED → RUNNING → COMPLETED / FAILED / CANCELED` |
| `started_at` | DATETIME | Início da execução |
| `ended_at` | DATETIME | Fim da execução |
| `total_work_time` | INTERVAL | Duração total |
| `error_message` | TEXT | Mensagem de erro (se falhou) |
| `error_stack` | TEXT | Stack trace completo (se falhou) |

### `item_run` (schema: `rpa_challenge`)

Rastreia cada item individualmente dentro de uma execução.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `item_id` | INT (PK) | Identificador único do item |
| `run_id` | INT (FK) | Referência à execução pai |
| `item_key` | VARCHAR | Chave de identificação do item |
| `status` | ENUM | `QUEUED → PROCESSING → COMPLETED / FAILED` |
| `attempt` | INT | Número de tentativas |
| `created_at` | DATETIME | Criação do item |
| `started_at` | DATETIME | Início do processamento |
| `completed_at` | DATETIME | Conclusão |
| `total_work_time` | INTERVAL | Tempo de processamento |
| `exception_reason` | VARCHAR | Motivo da falha (se aplicável) |

### `item` (schema: `rpa_challenge`)

Armazena os dados do formulário e o resultado.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INT (PK) | Identificador único |
| `item_id` | INT (FK) | Referência ao item_run |
| `First_Name` | VARCHAR | Primeiro nome |
| `Last_Name` | VARCHAR | Sobrenome |
| `Company_Name` | VARCHAR | Empresa |
| `Role_in_Company` | VARCHAR | Cargo |
| `Address` | VARCHAR | Endereço |
| `Email` | VARCHAR | E-mail |
| `Phone_Number` | VARCHAR | Telefone |
| `result` | VARCHAR | Taxa de sucesso capturada do site |

---

## Logs

Os logs são gerados automaticamente em múltiplos destinos:

| Destino | Localização | Formato |
|---------|-------------|---------|
| Console | Terminal | `TIMESTAMP - LOGGER - [LEVEL] - mensagem` |
| Arquivo | `logs/app<YYYY-MM-DD>.log` | Mesmo formato (um arquivo por dia) |
| Banco | Tabela de logs (futuro) | Erros críticos persistidos |

Exemplo de saída:
```
2026-05-11 10:30:00,123 - rpa_challenge - [INFO] - Iniciando execução. run_id=42
2026-05-11 10:30:01,456 - rpa_challenge - [INFO] - 10 itens lidos do Excel
2026-05-11 10:30:02,789 - rpa_challenge - [INFO] - 10 itens persistidos no banco
2026-05-11 10:30:15,000 - rpa_challenge - [INFO] - Item 1/10 concluído: João Silva
2026-05-11 10:31:00,000 - rpa_challenge - [INFO] - Taxa de sucesso: 100%
```

---

## Diretórios criados automaticamente

Na primeira execução, os seguintes diretórios são criados automaticamente pelo bot:

| Diretório | Propósito |
|-----------|-----------|
| `logs/` | Arquivos de log diários |
| `downloads/` | Downloads realizados pelo browser |
| `secret/` | Credenciais criptografadas do banco |

---

## Status de execução

### Processo (`process_run`)

```
SCHEDULED → RUNNING → COMPLETED
                    ↘ FAILED
                    ↘ CANCELED
```

### Item (`item_run`)

```
QUEUED → PROCESSING → COMPLETED
                    ↘ FAILED
                    ↘ EXCEPTION
                    ↘ ON_HOLD
                    ↘ DEFERRED
```

---

## Tecnologias utilizadas

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| [Python](https://python.org) | >=3.11 | Linguagem principal |
| [Playwright](https://playwright.dev/python/) | ^1.58.0 | Automação do browser |
| [SQLAlchemy](https://sqlalchemy.org) | — | ORM e acesso ao banco |
| [Alembic](https://alembic.sqlalchemy.org) | ^1.17.0 | Migrations do banco |
| [psycopg](https://www.psycopg.org/) | 3.2.9 | Driver PostgreSQL |
| [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | ^2.11.0 | Gerenciamento de configuração |
| [Pandas](https://pandas.pydata.org) | ^3.0.1 | Leitura e processamento do Excel |
| [openpyxl](https://openpyxl.readthedocs.io) | ^3.1.5 | Suporte a arquivos `.xlsx` |
| [cryptography](https://cryptography.io) | ^46.0.2 | Criptografia das credenciais (Fernet) |
| [BotCity Maestro SDK](https://botcity.dev) | ^0.9.0 | Integração com orquestrador RPA |
| [pytz](https://pythonhosted.org/pytz/) | ^2025.2 | Suporte a fusos horários |

---

## Integração com BotCity Maestro (opcional)

O bot possui integração nativa com o [BotCity Maestro](https://botcity.dev), permitindo:

- Execução agendada e orquestrada
- Monitoramento centralizado de execuções
- Alertas de falha via plataforma

Quando executado localmente (fora do Maestro), o bot detecta automaticamente que não está em ambiente de orquestração e continua funcionando normalmente.
