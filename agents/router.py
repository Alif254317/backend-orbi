from agno.models.openai import OpenAIResponses
from agno.team import Team, TeamMode

from config import LLM_MODEL, LLM_BASE_URL, OPENAI_API_KEY
from agents.general import create_general_agent
from agents.agenda import create_agenda_agent
from agents.shopping import create_shopping_agent
from agents.finance import create_finance_agent
from agents.tasks import create_tasks_agent
from agents.routines import create_routines_agent
from agents.ideas import create_ideas_agent

ROUTER_INSTRUCTIONS = """Você é o roteador da Arara AI. Sua função é analisar a mensagem
do usuário e direcioná-la para o agente especialista mais adequado.

Agentes disponíveis:
- Agenda: eventos, compromissos, lembretes, reuniões, datas marcadas
  Exemplos: "me lembra amanhã de ligar pro João", "quais meus compromissos hoje?",
  "marca reunião segunda às 14h", "tenho algo agendado essa semana?"

- Compras: lista de compras, itens para comprar no mercado/farmácia/etc.
  Exemplos: "adiciona leite e ovos na lista", "o que tem na minha lista?",
  "marca o arroz como comprado", "remove o pão da lista"

- Finanças: gastos, receitas, controle financeiro pessoal
  Exemplos: "gastei 45 no almoço", "recebi 3000 de salário", "quanto gastei esse mês?",
  "meu saldo", "resumo dos gastos da semana"

- Tarefas: to-do, tarefas com prazo e prioridade
  Exemplos: "preciso entregar o relatório até sexta", "lista minhas tarefas",
  "conclui a tarefa do relatório", "o que tenho pra fazer hoje?"

- Rotinas: hábitos recorrentes que se repetem (remédios, água, alimentação,
  exercício, higiene, meditação, sono). Tem horários específicos e recorrência.
  Exemplos: "tomar Losartana todo dia às 8h e 20h", "beber 8 copos de água por dia",
  "academia segunda, quarta e sexta às 18h", "o que tenho de rotina hoje?"

- Ideias: captura e estruturação de pensamentos, insights, dúvidas e ideias livres.
  Quando o usuário quer "anotar" algo ou expressa um pensamento/ideia solto.
  Exemplos: "anota essa ideia: criar app de receitas", "me lembra de pesquisar X",
  "tive um insight sobre Y", "quais ideias eu salvei?"

- General: conversas gerais, perguntas, dúvidas, qualquer assunto que não se
  encaixe nos módulos especializados

Analise a intenção da mensagem e direcione para o especialista certo.
"""


def get_router(session_id: str | None = None, user_id: str | None = None) -> Team:
    """Create the router team that directs messages to the right agent."""
    if not user_id:
        raise ValueError("user_id is required")

    agenda = create_agenda_agent(user_id=user_id, session_id=session_id)
    shopping = create_shopping_agent(user_id=user_id, session_id=session_id)
    finance = create_finance_agent(user_id=user_id, session_id=session_id)
    tasks = create_tasks_agent(user_id=user_id, session_id=session_id)
    routines = create_routines_agent(user_id=user_id, session_id=session_id)
    ideas = create_ideas_agent(user_id=user_id, session_id=session_id)
    general = create_general_agent(session_id=session_id)

    return Team(
        name="Arara Router",
        mode=TeamMode.route,
        model=OpenAIResponses(
            id=LLM_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=LLM_BASE_URL,
        ),
        members=[agenda, shopping, finance, tasks, routines, ideas, general],
        instructions=ROUTER_INSTRUCTIONS,
        session_id=session_id,
        markdown=False,
    )
