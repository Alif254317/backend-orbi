from datetime import datetime, timedelta
from typing import Callable

from tools.supabase_client import get_supabase


def build_agenda_tools(user_id: str) -> list[Callable]:
    """Build agenda CRUD tools bound to a specific user_id."""
    sb = get_supabase()

    def create_event(
        title: str,
        start_at: str,
        description: str = "",
        location: str = "",
        reminder_minutes: int = 30,
        end_at: str = "",
    ) -> str:
        """Cria um novo evento/compromisso/lembrete na agenda do usuário.

        Args:
            title: Título do evento (obrigatório).
            start_at: Data/hora de início em formato ISO 8601 (ex: '2026-04-20T14:30:00').
            description: Descrição opcional do evento.
            location: Local do evento (opcional).
            reminder_minutes: Minutos antes do evento para lembrete (padrão 30).
            end_at: Data/hora de término em formato ISO 8601 (opcional).
        """
        data = {
            "user_id": user_id,
            "title": title,
            "start_at": start_at,
            "reminder_minutes": reminder_minutes,
        }
        if description:
            data["description"] = description
        if location:
            data["location"] = location
        if end_at:
            data["end_at"] = end_at

        try:
            result = sb.table("events").insert(data).execute()
            event = result.data[0]
            return f"Evento criado: {event['title']} em {event['start_at']} (id={event['id']})"
        except Exception as e:
            return f"Erro ao criar evento: {e}"

    def list_events(
        date_from: str = "",
        date_to: str = "",
        limit: int = 20,
    ) -> str:
        """Lista eventos do usuário em um período.

        Args:
            date_from: Data inicial em ISO 8601 (padrão: hoje).
            date_to: Data final em ISO 8601 (padrão: 7 dias a partir de hoje).
            limit: Número máximo de eventos a retornar (padrão 20).
        """
        try:
            if not date_from:
                date_from = datetime.now().isoformat()
            if not date_to:
                date_to = (datetime.now() + timedelta(days=7)).isoformat()

            result = (
                sb.table("events")
                .select("*")
                .eq("user_id", user_id)
                .gte("start_at", date_from)
                .lte("start_at", date_to)
                .order("start_at")
                .limit(limit)
                .execute()
            )

            if not result.data:
                return "Nenhum evento encontrado no período."

            lines = [f"{len(result.data)} evento(s) encontrado(s):"]
            for e in result.data:
                marker = "✓" if e["is_completed"] else "○"
                lines.append(f"{marker} {e['start_at']} - {e['title']} (id={e['id']})")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro ao listar eventos: {e}"

    def get_today_events() -> str:
        """Retorna todos os eventos agendados para hoje."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return list_events(today.isoformat(), tomorrow.isoformat())

    def update_event(
        event_id: str,
        title: str = "",
        start_at: str = "",
        description: str = "",
        location: str = "",
        is_completed: bool | None = None,
    ) -> str:
        """Atualiza um evento existente.

        Args:
            event_id: UUID do evento a atualizar.
            title: Novo título (opcional).
            start_at: Nova data/hora ISO 8601 (opcional).
            description: Nova descrição (opcional).
            location: Novo local (opcional).
            is_completed: Marcar como concluído (opcional).
        """
        updates = {}
        if title:
            updates["title"] = title
        if start_at:
            updates["start_at"] = start_at
        if description:
            updates["description"] = description
        if location:
            updates["location"] = location
        if is_completed is not None:
            updates["is_completed"] = is_completed

        if not updates:
            return "Nenhuma alteração informada."

        try:
            result = (
                sb.table("events")
                .update(updates)
                .eq("id", event_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                return f"Evento {event_id} não encontrado."
            return f"Evento atualizado: {result.data[0]['title']}"
        except Exception as e:
            return f"Erro ao atualizar evento: {e}"

    def delete_event(event_id: str) -> str:
        """Remove um evento da agenda.

        Args:
            event_id: UUID do evento a remover.
        """
        try:
            result = (
                sb.table("events")
                .delete()
                .eq("id", event_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                return f"Evento {event_id} não encontrado."
            return f"Evento removido: {result.data[0]['title']}"
        except Exception as e:
            return f"Erro ao remover evento: {e}"

    return [create_event, list_events, get_today_events, update_event, delete_event]
