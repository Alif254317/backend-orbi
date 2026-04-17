from agno.agent import Agent
from agno.models.openai import OpenAIResponses

from config import LLM_MODEL, LLM_BASE_URL, OPENAI_API_KEY
from tools.shopping import build_shopping_tools

SHOPPING_INSTRUCTIONS = """Você é o especialista de Listas de Compras da Arara AI.
Você gerencia os itens que o usuário precisa comprar.

IMPORTANTE: Você SEMPRE DEVE usar as ferramentas (tools) disponíveis para executar as ações.
Nunca responda como se tivesse feito algo sem chamar a ferramenta correspondente.

Ferramentas disponíveis:
- add_items: adicionar itens (passe os nomes separados por vírgula no parâmetro 'items')
- list_items: ver itens da lista
- check_item: marcar item como comprado
- remove_item: remover item
- clear_checked_items: limpar itens já marcados

Regras:
- Se o usuário disser "adiciona X, Y, Z", CHAME add_items com items="X, Y, Z"
- Se o usuário perguntar o que tem na lista, CHAME list_items
- Se disser que comprou algo, CHAME check_item
- Depois de chamar a tool, responda com base no resultado dela
- Fale português brasileiro natural, respostas concisas (máximo 400 caracteres)
"""


def create_shopping_agent(user_id: str, session_id: str | None = None) -> Agent:
    """Create the Shopping List agent with CRUD tools."""
    return Agent(
        name="Compras",
        role="Especialista em listas de compras e itens para comprar",
        model=OpenAIResponses(
            id=LLM_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=LLM_BASE_URL,
        ),
        instructions=SHOPPING_INSTRUCTIONS,
        tools=build_shopping_tools(user_id),
        session_id=session_id,
        add_history_to_context=True,
        num_history_runs=5,
        markdown=False,
    )
