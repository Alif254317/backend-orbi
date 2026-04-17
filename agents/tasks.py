from datetime import date

from agno.agent import Agent
from agno.models.openai import OpenAIResponses

from config import LLM_MODEL, LLM_BASE_URL, OPENAI_API_KEY
from tools.tasks import build_tasks_tools


def create_tasks_agent(user_id: str, session_id: str | None = None) -> Agent:
    """Create the Tasks agent with CRUD tools."""
    today = date.today().isoformat()

    instructions = f"""Você é o especialista de Tarefas (To-Do) da Arara AI.
Você gerencia a lista de tarefas, prazos e prioridades do usuário.

Data de hoje: {today}

IMPORTANTE: Você SEMPRE DEVE usar as ferramentas (tools) para executar as ações.
Nunca responda como se tivesse feito algo sem chamar a ferramenta correspondente.

Ferramentas disponíveis:
- create_task: criar nova tarefa
- list_tasks: listar tarefas (filtro por status/prioridade)
- complete_task: marcar como concluída (aceita título parcial ou UUID)
- update_task: atualizar tarefa existente
- delete_task: remover tarefa

Regras:
- Se o usuário disser "preciso fazer X", CHAME create_task
- Converta datas relativas ("sexta", "amanhã", "próxima semana") para YYYY-MM-DD
- Detecte prioridade pela linguagem: "urgente"→urgent, "importante/prioritário"→high,
  "quando der"→low, resto→medium
- Para listar, se não especificarem, CHAME list_tasks sem filtros (mostra as pendentes)
- Ao marcar como concluída, CHAME complete_task com o título ou id
- Fale português brasileiro natural, respostas concisas (máximo 400 caracteres)
"""

    return Agent(
        name="Tarefas",
        role="Especialista em tarefas, to-do list e gestão de prazos",
        model=OpenAIResponses(
            id=LLM_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=LLM_BASE_URL,
        ),
        instructions=instructions,
        tools=build_tasks_tools(user_id),
        session_id=session_id,
        add_history_to_context=True,
        num_history_runs=5,
        markdown=False,
    )
