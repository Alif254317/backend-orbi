from datetime import date, timedelta
from typing import Callable

from tools.supabase_client import get_supabase


def _find_category(sb, user_id: str, name_or_type: str, type_hint: str = "") -> str | None:
    """Find category by name (user's own or default), falling back to 'Outros' of the given type."""
    if not name_or_type:
        return None

    q = sb.table("finance_categories").select("id, name, type")
    q = q.or_(f"user_id.eq.{user_id},is_default.eq.true")
    q = q.ilike("name", f"%{name_or_type}%")
    result = q.limit(1).execute()
    return result.data[0]["id"] if result.data else None


def build_finance_tools(user_id: str) -> list[Callable]:
    """Build finance CRUD tools bound to a specific user_id."""
    sb = get_supabase()

    def add_transaction(
        amount: float,
        type: str,
        description: str = "",
        category: str = "",
        tx_date: str = "",
    ) -> str:
        """Registra uma nova transação financeira (gasto ou receita).

        Args:
            amount: Valor da transação em reais (sempre positivo).
            type: 'expense' para gasto ou 'income' para receita.
            description: Descrição da transação (ex: 'Almoço no restaurante').
            category: Nome da categoria (ex: 'Alimentação', 'Salário').
            tx_date: Data da transação em formato YYYY-MM-DD (padrão: hoje).
        """
        if type not in ("income", "expense"):
            return "Erro: type deve ser 'income' ou 'expense'."
        if amount < 0:
            amount = abs(amount)

        data = {
            "user_id": user_id,
            "type": type,
            "amount": amount,
        }
        if description:
            data["description"] = description
        if tx_date:
            data["date"] = tx_date

        if category:
            cat_id = _find_category(sb, user_id, category)
            if cat_id:
                data["category_id"] = cat_id

        try:
            result = sb.table("finance_transactions").insert(data).execute()
            tx = result.data[0]
            label = "Gasto" if type == "expense" else "Receita"
            return f"{label} de R$ {tx['amount']:.2f} registrado: {description or 'sem descrição'} (id={tx['id']})"
        except Exception as e:
            return f"Erro ao registrar transação: {e}"

    def get_balance(period: str = "month") -> str:
        """Retorna o saldo (receitas - gastos) de um período.

        Args:
            period: 'today', 'week', 'month' (padrão) ou 'year'.
        """
        today = date.today()
        if period == "today":
            date_from = today
        elif period == "week":
            date_from = today - timedelta(days=7)
        elif period == "year":
            date_from = today.replace(month=1, day=1)
        else:
            date_from = today.replace(day=1)

        try:
            result = (
                sb.table("finance_transactions")
                .select("type, amount")
                .eq("user_id", user_id)
                .gte("date", date_from.isoformat())
                .execute()
            )
            income = sum(float(t["amount"]) for t in result.data if t["type"] == "income")
            expense = sum(float(t["amount"]) for t in result.data if t["type"] == "expense")
            balance = income - expense
            return (
                f"Período ({period}): "
                f"Receitas R$ {income:.2f}, "
                f"Gastos R$ {expense:.2f}, "
                f"Saldo R$ {balance:.2f}"
            )
        except Exception as e:
            return f"Erro ao calcular saldo: {e}"

    def get_summary_by_category(period: str = "month") -> str:
        """Retorna o total gasto/recebido agrupado por categoria no período.

        Args:
            period: 'today', 'week', 'month' (padrão) ou 'year'.
        """
        today = date.today()
        if period == "today":
            date_from = today
        elif period == "week":
            date_from = today - timedelta(days=7)
        elif period == "year":
            date_from = today.replace(month=1, day=1)
        else:
            date_from = today.replace(day=1)

        try:
            result = (
                sb.table("finance_transactions")
                .select("type, amount, category_id, finance_categories(name)")
                .eq("user_id", user_id)
                .gte("date", date_from.isoformat())
                .execute()
            )
            if not result.data:
                return f"Nenhuma transação no período ({period})."

            totals = {}
            for t in result.data:
                cat_name = (t.get("finance_categories") or {}).get("name") or "Sem categoria"
                key = f"{t['type']}:{cat_name}"
                totals[key] = totals.get(key, 0) + float(t["amount"])

            lines = [f"Resumo ({period}):"]
            for key, total in sorted(totals.items(), key=lambda x: -x[1]):
                tx_type, cat = key.split(":", 1)
                label = "→" if tx_type == "expense" else "←"
                lines.append(f"{label} {cat}: R$ {total:.2f}")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro ao calcular resumo: {e}"

    def list_transactions(
        date_from: str = "",
        date_to: str = "",
        type: str = "",
        limit: int = 20,
    ) -> str:
        """Lista transações recentes do usuário.

        Args:
            date_from: Data inicial YYYY-MM-DD (padrão: início do mês atual).
            date_to: Data final YYYY-MM-DD (padrão: hoje).
            type: Filtrar por 'income' ou 'expense' (opcional).
            limit: Máximo de resultados (padrão 20).
        """
        if not date_from:
            date_from = date.today().replace(day=1).isoformat()
        if not date_to:
            date_to = date.today().isoformat()

        try:
            q = (
                sb.table("finance_transactions")
                .select("id, type, amount, description, date, finance_categories(name)")
                .eq("user_id", user_id)
                .gte("date", date_from)
                .lte("date", date_to)
            )
            if type in ("income", "expense"):
                q = q.eq("type", type)
            result = q.order("date", desc=True).limit(limit).execute()

            if not result.data:
                return "Nenhuma transação encontrada."

            lines = [f"{len(result.data)} transação(ões):"]
            for t in result.data:
                sign = "-" if t["type"] == "expense" else "+"
                cat = (t.get("finance_categories") or {}).get("name") or "-"
                desc = t.get("description") or ""
                lines.append(f"{t['date']} {sign}R${t['amount']:.2f} [{cat}] {desc}")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro ao listar transações: {e}"

    def delete_transaction(transaction_id: str) -> str:
        """Remove uma transação financeira.

        Args:
            transaction_id: UUID da transação a remover.
        """
        try:
            result = (
                sb.table("finance_transactions")
                .delete()
                .eq("id", transaction_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                return "Transação não encontrada."
            return f"Transação removida: R$ {result.data[0]['amount']:.2f}"
        except Exception as e:
            return f"Erro ao remover: {e}"

    return [add_transaction, get_balance, get_summary_by_category, list_transactions, delete_transaction]
