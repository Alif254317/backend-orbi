from agno.agent import Agent
from agno.models.openai import OpenAIResponses

from config import LLM_MODEL, LLM_BASE_URL, OPENAI_API_KEY

GENERAL_PROMPT = """Você é a Arara, uma assistente pessoal inteligente e simpática.

Regras:
- Fale português brasileiro natural e amigável
- Respostas concisas e diretas (máximo 500 caracteres)
- Você ajuda com perguntas gerais, conversas e dúvidas
- Se o usuário pedir algo relacionado a agenda, lista de compras, finanças ou tarefas,
  responda normalmente mas avise que em breve terá módulos dedicados para isso
- Nunca invente dados ou informações
- Seja prestativa e proativa em sugestões
"""


def create_general_agent(session_id: str | None = None) -> Agent:
    """Create the general-purpose chat agent."""
    return Agent(
        name="General",
        role="Assistente geral para conversas e perguntas",
        model=OpenAIResponses(
            id=LLM_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=LLM_BASE_URL,
        ),
        instructions=GENERAL_PROMPT,
        session_id=session_id,
        add_history_to_context=True,
        num_history_runs=10,
        markdown=False,
    )
