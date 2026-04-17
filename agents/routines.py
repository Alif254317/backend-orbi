from datetime import date

from agno.agent import Agent
from agno.models.openai import OpenAIResponses

from config import LLM_MODEL, LLM_BASE_URL, OPENAI_API_KEY
from tools.routines import build_routines_tools


def create_routines_agent(user_id: str, session_id: str | None = None) -> Agent:
    """Create the Routines agent with CRUD tools."""
    today = date.today().isoformat()

    instructions = f"""Você é o especialista de Rotinas/Hábitos da Arara AI. Você gerencia
rotinas recorrentes do usuário como remédios, hidratação, alimentação, exercícios, etc.

Data de hoje: {today}

IMPORTANTE: Você SEMPRE DEVE usar as ferramentas (tools) para executar as ações.
Nunca responda como se tivesse feito algo sem chamar a ferramenta.

Ferramentas disponíveis:
- create_routine: criar rotina (passe title, times no formato 'HH:MM,HH:MM', category)
- list_routines: listar rotinas ativas
- log_routine: marcar como feita agora (precisa do routine_id)
- get_today_routines: listar rotinas de hoje com status
- update_routine: atualizar rotina
- delete_routine: remover rotina

Categorias válidas:
medication (remédios), hydration (água), food (refeições), exercise (treino),
mind (meditação), hygiene (higiene), sleep (sono), study (estudo), home (casa),
social (pessoas), work (trabalho), other (outros)

Regras:
- Se o usuário disser "tomar remédio X às 8h e 20h", CHAME create_routine com
  title="Tomar X", times="08:00,20:00", category="medication"
- Se disser "beber 2L de água / 8 copos", use target_count=8, category="hydration"
- Para dias específicos ("seg, qua, sex"), passe recurrence="weekly" e weekdays="1,3,5"
- Fale português brasileiro natural, respostas concisas (máximo 400 caracteres)
"""

    return Agent(
        name="Rotinas",
        role="Especialista em rotinas, hábitos recorrentes e tracking diário",
        model=OpenAIResponses(
            id=LLM_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=LLM_BASE_URL,
        ),
        instructions=instructions,
        tools=build_routines_tools(user_id),
        session_id=session_id,
        add_history_to_context=True,
        num_history_runs=5,
        markdown=False,
    )
