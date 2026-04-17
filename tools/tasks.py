from typing import Callable

from tools.supabase_client import get_supabase


def build_tasks_tools(user_id: str) -> list[Callable]:
    """Build task CRUD tools bound to a specific user_id."""
    sb = get_supabase()

    def create_task(
        title: str,
        due_date: str = "",
        priority: str = "medium",
        description: str = "",
    ) -> str:
        """Cria uma nova tarefa (to-do).

        Args:
            title: Título da tarefa (obrigatório).
            due_date: Data limite em formato YYYY-MM-DD (opcional).
            priority: Prioridade: 'low', 'medium' (padrão), 'high' ou 'urgent'.
            description: Descrição detalhada (opcional).
        """
        if priority not in ("low", "medium", "high", "urgent"):
            priority = "medium"

        data = {
            "user_id": user_id,
            "title": title,
            "priority": priority,
        }
        if due_date:
            data["due_date"] = due_date
        if description:
            data["description"] = description

        try:
            result = sb.table("tasks").insert(data).execute()
            task = result.data[0]
            due = f" (até {task['due_date']})" if task.get("due_date") else ""
            return f"Tarefa criada: {task['title']} [prioridade: {priority}]{due} (id={task['id']})"
        except Exception as e:
            return f"Erro ao criar tarefa: {e}"

    def list_tasks(
        status: str = "",
        priority: str = "",
        limit: int = 20,
    ) -> str:
        """Lista tarefas do usuário.

        Args:
            status: Filtrar por 'pending', 'in_progress', 'completed' ou 'cancelled' (opcional).
            priority: Filtrar por 'low', 'medium', 'high' ou 'urgent' (opcional).
            limit: Máximo de resultados (padrão 20).
        """
        try:
            q = sb.table("tasks").select("*").eq("user_id", user_id)
            if status:
                q = q.eq("status", status)
            if priority:
                q = q.eq("priority", priority)
            result = q.order("due_date", desc=False).order("priority").limit(limit).execute()

            if not result.data:
                return "Nenhuma tarefa encontrada."

            priority_icon = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            status_icon = {
                "pending": "○",
                "in_progress": "◐",
                "completed": "✓",
                "cancelled": "✗",
            }

            lines = [f"{len(result.data)} tarefa(s):"]
            for t in result.data:
                p = priority_icon.get(t["priority"], "")
                s = status_icon.get(t["status"], "")
                due = f" [até {t['due_date']}]" if t.get("due_date") else ""
                lines.append(f"{s} {p} {t['title']}{due} (id={t['id']})")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro ao listar: {e}"

    def complete_task(task_id_or_title: str) -> str:
        """Marca uma tarefa como concluída.

        Args:
            task_id_or_title: UUID ou título (parcial) da tarefa a concluir.
        """
        try:
            # Try UUID first
            q = sb.table("tasks").select("id, title").eq("user_id", user_id)
            if len(task_id_or_title) == 36 and task_id_or_title.count("-") == 4:
                result = q.eq("id", task_id_or_title).maybe_single().execute()
            else:
                result = (
                    q.ilike("title", f"%{task_id_or_title}%")
                    .neq("status", "completed")
                    .limit(1)
                    .execute()
                )
                result.data = result.data[0] if result.data else None

            if not result.data:
                return f"Tarefa '{task_id_or_title}' não encontrada."

            updated = (
                sb.table("tasks")
                .update({"status": "completed"})
                .eq("id", result.data["id"])
                .execute()
            )
            return f"Tarefa concluída: {updated.data[0]['title']}"
        except Exception as e:
            return f"Erro ao concluir tarefa: {e}"

    def update_task(
        task_id: str,
        title: str = "",
        due_date: str = "",
        priority: str = "",
        status: str = "",
        description: str = "",
    ) -> str:
        """Atualiza uma tarefa existente.

        Args:
            task_id: UUID da tarefa.
            title: Novo título (opcional).
            due_date: Nova data limite YYYY-MM-DD (opcional).
            priority: Nova prioridade (opcional).
            status: Novo status (opcional).
            description: Nova descrição (opcional).
        """
        updates = {}
        if title:
            updates["title"] = title
        if due_date:
            updates["due_date"] = due_date
        if priority in ("low", "medium", "high", "urgent"):
            updates["priority"] = priority
        if status in ("pending", "in_progress", "completed", "cancelled"):
            updates["status"] = status
        if description:
            updates["description"] = description

        if not updates:
            return "Nenhuma alteração informada."

        try:
            result = (
                sb.table("tasks")
                .update(updates)
                .eq("id", task_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                return f"Tarefa {task_id} não encontrada."
            return f"Tarefa atualizada: {result.data[0]['title']}"
        except Exception as e:
            return f"Erro ao atualizar: {e}"

    def delete_task(task_id: str) -> str:
        """Remove uma tarefa.

        Args:
            task_id: UUID da tarefa a remover.
        """
        try:
            result = (
                sb.table("tasks")
                .delete()
                .eq("id", task_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                return "Tarefa não encontrada."
            return f"Tarefa removida: {result.data[0]['title']}"
        except Exception as e:
            return f"Erro ao remover: {e}"

    return [create_task, list_tasks, complete_task, update_task, delete_task]
