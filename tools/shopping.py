from typing import Callable

from tools.supabase_client import get_supabase


def _get_or_create_default_list(sb, user_id: str) -> str:
    """Get default active list for user, creating one if needed."""
    result = (
        sb.table("shopping_lists")
        .select("id")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]["id"]

    created = (
        sb.table("shopping_lists")
        .insert({"user_id": user_id, "name": "Minha Lista"})
        .execute()
    )
    return created.data[0]["id"]


def _find_list_by_name(sb, user_id: str, name: str) -> str | None:
    result = (
        sb.table("shopping_lists")
        .select("id")
        .eq("user_id", user_id)
        .ilike("name", name)
        .limit(1)
        .execute()
    )
    return result.data[0]["id"] if result.data else None


def build_shopping_tools(user_id: str) -> list[Callable]:
    """Build shopping list CRUD tools bound to a specific user_id."""
    sb = get_supabase()

    def add_items(
        items: str,
        list_name: str = "",
        category: str = "",
    ) -> str:
        """Adiciona um ou mais itens à lista de compras.

        Args:
            items: Itens separados por vírgula (ex: 'leite, ovos, pão 2kg').
            list_name: Nome da lista (opcional, usa a lista padrão ativa).
            category: Categoria dos itens (ex: 'alimentos', 'limpeza').
        """
        list_id = (
            _find_list_by_name(sb, user_id, list_name)
            if list_name
            else _get_or_create_default_list(sb, user_id)
        )
        if not list_id:
            return f"Lista '{list_name}' não encontrada."

        rows = []
        for item in [x.strip() for x in items.split(",") if x.strip()]:
            row = {"list_id": list_id, "name": item}
            if category:
                row["category"] = category
            rows.append(row)

        if not rows:
            return "Nenhum item informado."

        try:
            result = sb.table("shopping_items").insert(rows).execute()
            names = ", ".join(r["name"] for r in result.data)
            return f"{len(result.data)} item(ns) adicionado(s): {names}"
        except Exception as e:
            return f"Erro ao adicionar itens: {e}"

    def list_items(list_name: str = "", show_checked: bool = False) -> str:
        """Lista itens da lista de compras.

        Args:
            list_name: Nome da lista (opcional, usa a lista padrão ativa).
            show_checked: Se True, mostra também itens já marcados.
        """
        list_id = (
            _find_list_by_name(sb, user_id, list_name)
            if list_name
            else _get_or_create_default_list(sb, user_id)
        )
        if not list_id:
            return f"Lista '{list_name}' não encontrada."

        q = sb.table("shopping_items").select("*").eq("list_id", list_id)
        if not show_checked:
            q = q.eq("is_checked", False)

        result = q.order("created_at").execute()

        if not result.data:
            return "Lista vazia."

        lines = [f"{len(result.data)} item(ns):"]
        for it in result.data:
            marker = "✓" if it["is_checked"] else "○"
            qty = f"{it['quantity']}x " if it["quantity"] > 1 else ""
            lines.append(f"{marker} {qty}{it['name']} (id={it['id']})")
        return "\n".join(lines)

    def check_item(item_name: str, list_name: str = "") -> str:
        """Marca um item como comprado/concluído.

        Args:
            item_name: Nome do item a marcar (busca parcial case-insensitive).
            list_name: Nome da lista (opcional, usa a lista padrão).
        """
        list_id = (
            _find_list_by_name(sb, user_id, list_name)
            if list_name
            else _get_or_create_default_list(sb, user_id)
        )
        if not list_id:
            return f"Lista '{list_name}' não encontrada."

        found = (
            sb.table("shopping_items")
            .select("id, name")
            .eq("list_id", list_id)
            .ilike("name", f"%{item_name}%")
            .eq("is_checked", False)
            .limit(1)
            .execute()
        )
        if not found.data:
            return f"Item '{item_name}' não encontrado na lista."

        item = found.data[0]
        sb.table("shopping_items").update({"is_checked": True}).eq("id", item["id"]).execute()
        return f"Item marcado: {item['name']}"

    def remove_item(item_name: str, list_name: str = "") -> str:
        """Remove um item da lista de compras.

        Args:
            item_name: Nome do item a remover (busca parcial case-insensitive).
            list_name: Nome da lista (opcional).
        """
        list_id = (
            _find_list_by_name(sb, user_id, list_name)
            if list_name
            else _get_or_create_default_list(sb, user_id)
        )
        if not list_id:
            return f"Lista '{list_name}' não encontrada."

        found = (
            sb.table("shopping_items")
            .select("id, name")
            .eq("list_id", list_id)
            .ilike("name", f"%{item_name}%")
            .limit(1)
            .execute()
        )
        if not found.data:
            return f"Item '{item_name}' não encontrado."

        item = found.data[0]
        sb.table("shopping_items").delete().eq("id", item["id"]).execute()
        return f"Item removido: {item['name']}"

    def clear_checked_items(list_name: str = "") -> str:
        """Remove todos os itens já marcados como comprados.

        Args:
            list_name: Nome da lista (opcional, usa a lista padrão).
        """
        list_id = (
            _find_list_by_name(sb, user_id, list_name)
            if list_name
            else _get_or_create_default_list(sb, user_id)
        )
        if not list_id:
            return f"Lista '{list_name}' não encontrada."

        result = (
            sb.table("shopping_items")
            .delete()
            .eq("list_id", list_id)
            .eq("is_checked", True)
            .execute()
        )
        return f"{len(result.data)} item(ns) marcado(s) removido(s)."

    return [add_items, list_items, check_item, remove_item, clear_checked_items]
