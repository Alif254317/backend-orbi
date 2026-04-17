from datetime import datetime

from agno.agent import Agent
from agno.models.openai import OpenAIResponses

from config import LLM_MODEL, LLM_BASE_URL, OPENAI_API_KEY
from tools.agenda import build_agenda_tools


def create_agenda_agent(user_id: str, session_id: str | None = None) -> Agent:
    """Create the Agenda agent with CRUD tools for events."""
    now_iso = datetime.now().isoformat()

    instructions = f"""Você é o especialista de Agenda da Arara AI. Você gerencia eventos,
compromissos e lembretes do usuário.

Data/hora atual: {now_iso}

IMPORTANTE: Você SEMPRE DEVE usar as ferramentas (tools) para executar as ações.
Nunca responda como se tivesse feito algo sem chamar a ferramenta correspondente.

Ferramentas disponíveis:
- create_event: criar novo evento
- list_events: listar eventos de um período
- get_today_events: eventos de hoje
- update_event: atualizar evento existente
- delete_event: remover evento

Regras:
- Quando o usuário mencionar uma data relativa ("amanhã", "sexta", "daqui 2 horas"),
  converta para ISO 8601 completo antes de chamar as ferramentas
- Ao criar eventos, CHAME create_event e depois confirme com base no resultado
- Ao listar, CHAME list_events ou get_today_events
- Fale português brasileiro natural, respostas concisas (máximo 400 caracteres)
"""

    return Agent(
        name="Agenda",
        role="Especialista em agenda, eventos, compromissos e lembretes",
        model=OpenAIResponses(
            id=LLM_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=LLM_BASE_URL,
        ),
        instructions=instructions,
        tools=build_agenda_tools(user_id),
        session_id=session_id,
        add_history_to_context=True,
        num_history_runs=5,
        markdown=False,
    )
