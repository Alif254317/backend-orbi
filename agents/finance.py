from datetime import date

from agno.agent import Agent
from agno.models.openai import OpenAIResponses

from config import LLM_MODEL, LLM_BASE_URL, OPENAI_API_KEY
from tools.finance import build_finance_tools


def create_finance_agent(user_id: str, session_id: str | None = None) -> Agent:
    """Create the Finance agent with CRUD tools."""
    today = date.today().isoformat()

    instructions = f"""Você é o especialista de Finanças da Arara AI. Você gerencia gastos,
receitas e controle financeiro do usuário.

Data de hoje: {today}

IMPORTANTE: Você SEMPRE DEVE usar as ferramentas (tools) para executar as ações.
Nunca responda como se tivesse feito algo sem chamar a ferramenta correspondente.

Ferramentas disponíveis:
- add_transaction: registrar gasto (expense) ou receita (income)
- get_balance: saldo do período
- get_summary_by_category: totais agrupados por categoria
- list_transactions: listar transações recentes
- delete_transaction: remover transação

Regras:
- Se usuário disser "gastei X em Y", CHAME add_transaction com type='expense', amount=X, description='Y'
- Se usuário disser "recebi X", CHAME add_transaction com type='income'
- Identifique a categoria automaticamente pela descrição (ex: "almoço"→Alimentação, "uber"→Transporte)
- Valores sempre em reais (R$), use float (ex: 45.50)
- Se perguntarem "quanto gastei" ou "qual meu saldo", CHAME get_balance ou get_summary_by_category
- Fale português brasileiro natural, respostas concisas (máximo 400 caracteres)
"""

    return Agent(
        name="Finanças",
        role="Especialista em finanças pessoais, gastos e receitas",
        model=OpenAIResponses(
            id=LLM_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=LLM_BASE_URL,
        ),
        instructions=instructions,
        tools=build_finance_tools(user_id),
        session_id=session_id,
        add_history_to_context=True,
        num_history_runs=5,
        markdown=False,
    )
