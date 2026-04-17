# Arara AI — Backend

Backend do assistente pessoal Arara AI. Um roteador de agentes especializados (Agno + FastAPI) conversa com o usuário em linguagem natural e persiste os dados no Supabase. O app cliente consome tanto o endpoint de chat quanto as APIs REST de cada módulo.

## Stack

- **FastAPI** — servidor HTTP (endpoints de chat + REST por módulo)
- **Agno** — framework de agentes (um roteador `Team` em modo `route` encaminha para o especialista certo)
- **Supabase** (Postgres) — persistência
- **OpenAI / OpenRouter** — LLM (configurável via `LLM_BASE_URL`)

## Módulos

O router analisa a intenção da mensagem e delega para um dos agentes:

| Módulo    | Para que serve                                                           |
|-----------|--------------------------------------------------------------------------|
| `agenda`  | Eventos, compromissos, lembretes                                         |
| `shopping`| Lista de compras                                                         |
| `finance` | Gastos, receitas, saldo                                                  |
| `tasks`   | To-do com prazo e prioridade                                             |
| `routines`| Hábitos recorrentes (remédios, água, exercício, etc.)                    |
| `ideas`   | Captura de pensamentos/insights, estruturada pela IA                     |
| `general` | Conversa aberta para tudo que não se encaixa nos módulos acima           |

## Estrutura

```
backend/
├── app.py              # FastAPI: /chat, /modules, /health + routers REST
├── config.py           # Carrega .env (Supabase, LLM, host/porta)
├── requirements.txt
├── agents/             # Agentes Agno — um por domínio + router + general
│   ├── router.py       # Team em modo route que direciona para o especialista
│   ├── agenda.py
│   ├── shopping.py
│   ├── finance.py
│   ├── tasks.py
│   ├── routines.py
│   ├── ideas.py
│   └── general.py
├── api/                # Endpoints REST (CRUD) por módulo
│   ├── agenda.py
│   ├── shopping.py
│   ├── finance.py
│   ├── tasks.py
│   ├── routines.py
│   └── ideas.py
└── tools/              # Tools Agno que leem/escrevem no Supabase
    ├── supabase_client.py
    ├── agenda.py
    ├── shopping.py
    ├── finance.py
    ├── tasks.py
    ├── routines.py
    └── ideas.py
```

Fluxo: mensagem chega em `/chat` → `agents/router.py` classifica → agente especialista chama tools em `tools/*` → tools leem/gravam no Supabase.

## Setup

```bash
# 1. Clonar
git clone https://github.com/Alif254317/backend-orbi.git
cd backend-orbi

# 2. Ambiente
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Variáveis de ambiente
cp .env.example .env
# edite .env com suas chaves

# 4. Rodar
python app.py
```

Servidor sobe em `http://0.0.0.0:5050` (ajustável via `HOST`/`PORT`).

## Variáveis de ambiente

Veja `.env.example`. Principais:

- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_DB_URL` — credenciais do projeto Supabase
- `OPENAI_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` — LLM (compatível com OpenAI ou OpenRouter)
- `HOST`, `PORT` — bind do servidor (padrão `0.0.0.0:5050`)

## Endpoints principais

### Chat (roteado via Agno)

```http
POST /chat
Content-Type: application/json

{
  "session_id": "sess-123",
  "user_id": "user-uuid",
  "message": "gastei 45 no almoço hoje"
}
```

Resposta:

```json
{ "success": true, "data": { "content": "Registrei R$ 45,00..." } }
```

### REST por módulo

Cada módulo expõe rotas CRUD próprias sob seu prefixo (`/agenda`, `/shopping`, `/finance`, `/tasks`, `/routines`, `/ideas`). Veja os arquivos em `api/` para detalhes.

### Utilitários

- `GET /health` — status do serviço
- `GET /modules` — lista dos módulos habilitados (usado pelo app)

## Desenvolvimento

O `uvicorn` roda com `reload=True` ao executar `python app.py`, então mudanças em `agents/`, `api/` e `tools/` recarregam automaticamente.
