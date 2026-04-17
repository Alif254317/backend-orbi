from datetime import datetime, timedelta, date, time as dtime
from typing import Callable

from tools.supabase_client import get_supabase


VALID_CATEGORIES = {
    "medication", "hydration", "food", "exercise", "mind",
    "hygiene", "sleep", "study", "home", "social", "work", "other"
}


def _parse_times(times_str: str) -> list[str]:
    """Parse 'HH:MM' strings separated by commas into list."""
    result = []
    for t in [x.strip() for x in times_str.split(",") if x.strip()]:
        # Validate HH:MM
        try:
            dtime.fromisoformat(t if len(t) == 8 else f"{t}:00")
            result.append(t if len(t) >= 5 else t + ":00")
        except ValueError:
            pass
    return result


def _parse_weekdays(days_str: str) -> list[int]:
    """Parse '1,2,3' or day names into list of 1-7 (1=mon)."""
    if not days_str:
        return [1, 2, 3, 4, 5, 6, 7]
    mapping = {
        "seg": 1, "segunda": 1, "mon": 1, "monday": 1,
        "ter": 2, "terça": 2, "terca": 2, "tue": 2, "tuesday": 2,
        "qua": 3, "quarta": 3, "wed": 3, "wednesday": 3,
        "qui": 4, "quinta": 4, "thu": 4, "thursday": 4,
        "sex": 5, "sexta": 5, "fri": 5, "friday": 5,
        "sab": 6, "sábado": 6, "sabado": 6, "sat": 6, "saturday": 6,
        "dom": 7, "domingo": 7, "sun": 7, "sunday": 7,
    }
    result = set()
    for part in [p.strip().lower() for p in days_str.split(",")]:
        if part.isdigit():
            n = int(part)
            if 1 <= n <= 7:
                result.add(n)
        elif part in mapping:
            result.add(mapping[part])
    return sorted(result) if result else [1, 2, 3, 4, 5, 6, 7]


def build_routines_tools(user_id: str) -> list[Callable]:
    """Build routine CRUD tools bound to a specific user_id."""
    sb = get_supabase()

    def create_routine(
        title: str,
        times: str,
        category: str = "other",
        recurrence: str = "daily",
        weekdays: str = "",
        target_count: int = 0,
        description: str = "",
    ) -> str:
        """Cria uma nova rotina/hábito recorrente.

        Args:
            title: Título da rotina (ex: 'Tomar Losartana').
            times: Horários separados por vírgula no formato HH:MM (ex: '08:00,20:00').
            category: Categoria: medication, hydration, food, exercise, mind, hygiene, sleep, study, home, social, work, other.
            recurrence: 'daily' (padrão), 'weekly' ou 'custom'.
            weekdays: Dias da semana separados por vírgula (1=seg,7=dom) — usado se recurrence='weekly' (ex: '1,3,5').
            target_count: Meta numérica por dia (ex: 8 para 8 copos de água). 0 ou vazio = meta por horário.
            description: Descrição opcional.
        """
        if category not in VALID_CATEGORIES:
            category = "other"
        if recurrence not in ("daily", "weekly", "custom"):
            recurrence = "daily"

        times_list = _parse_times(times)
        if not times_list and target_count == 0:
            return "Erro: informe pelo menos um horário (ex: '08:00,20:00') ou uma meta."

        data = {
            "user_id": user_id,
            "title": title,
            "category": category,
            "recurrence": recurrence,
            "times": times_list,
            "weekdays": _parse_weekdays(weekdays) if recurrence == "weekly" else [1,2,3,4,5,6,7],
            "active": True,
        }
        if target_count > 0:
            data["target_count"] = target_count
        if description:
            data["description"] = description

        try:
            result = sb.table("routines").insert(data).execute()
            r = result.data[0]
            return f"Rotina criada: {r['title']} ({', '.join(times_list) if times_list else f'meta {target_count}'}) id={r['id']}"
        except Exception as e:
            return f"Erro ao criar rotina: {e}"

    def list_routines(active_only: bool = True, category: str = "") -> str:
        """Lista as rotinas do usuário.

        Args:
            active_only: Se True (padrão), mostra só as ativas.
            category: Filtrar por categoria (opcional).
        """
        try:
            q = sb.table("routines").select("*").eq("user_id", user_id)
            if active_only:
                q = q.eq("active", True)
            if category and category in VALID_CATEGORIES:
                q = q.eq("category", category)
            result = q.order("title").execute()

            if not result.data:
                return "Nenhuma rotina encontrada."

            lines = [f"{len(result.data)} rotina(s):"]
            for r in result.data:
                times = ", ".join(r.get("times") or []) or f"meta {r.get('target_count')}"
                lines.append(f"  [{r['category']}] {r['title']} — {times} (id={r['id']})")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro ao listar: {e}"

    def log_routine(routine_id: str, note: str = "") -> str:
        """Registra que o usuário completou a rotina agora (marca como feita).

        Args:
            routine_id: UUID da rotina.
            note: Observação opcional.
        """
        try:
            now = datetime.now()
            data = {
                "routine_id": routine_id,
                "user_id": user_id,
                "scheduled_at": now.isoformat(),
                "completed_at": now.isoformat(),
            }
            if note:
                data["note"] = note
            sb.table("routine_logs").insert(data).execute()
            return "Rotina registrada como concluída."
        except Exception as e:
            return f"Erro ao registrar: {e}"

    def get_today_routines() -> str:
        """Retorna as rotinas programadas para hoje com status (pendentes ou concluídas)."""
        try:
            today = date.today()
            weekday = today.isoweekday()  # 1=mon, 7=sun

            r_res = (
                sb.table("routines")
                .select("*")
                .eq("user_id", user_id)
                .eq("active", True)
                .execute()
            )
            routines = [r for r in r_res.data if weekday in (r.get("weekdays") or [])]

            start = datetime.combine(today, dtime.min).isoformat()
            end = datetime.combine(today, dtime.max).isoformat()
            logs_res = (
                sb.table("routine_logs")
                .select("routine_id, completed_at")
                .eq("user_id", user_id)
                .gte("scheduled_at", start)
                .lte("scheduled_at", end)
                .execute()
            )
            done_ids = {l["routine_id"] for l in logs_res.data if l.get("completed_at")}

            if not routines:
                return "Nenhuma rotina programada para hoje."

            lines = [f"Hoje ({today.isoformat()}):"]
            for r in routines:
                status = "✓" if r["id"] in done_ids else "○"
                times = ", ".join(r.get("times") or []) or f"meta {r.get('target_count')}"
                lines.append(f"{status} {r['title']} — {times}")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro ao buscar: {e}"

    def update_routine(
        routine_id: str,
        title: str = "",
        times: str = "",
        category: str = "",
        active: bool | None = None,
        description: str = "",
    ) -> str:
        """Atualiza uma rotina existente.

        Args:
            routine_id: UUID da rotina.
            title: Novo título (opcional).
            times: Novos horários HH:MM separados por vírgula (opcional).
            category: Nova categoria (opcional).
            active: Ativar/desativar (opcional).
            description: Nova descrição (opcional).
        """
        updates = {}
        if title:
            updates["title"] = title
        if times:
            updates["times"] = _parse_times(times)
        if category and category in VALID_CATEGORIES:
            updates["category"] = category
        if active is not None:
            updates["active"] = active
        if description:
            updates["description"] = description

        if not updates:
            return "Nenhuma alteração informada."
        try:
            result = (
                sb.table("routines")
                .update(updates)
                .eq("id", routine_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                return "Rotina não encontrada."
            return f"Rotina atualizada: {result.data[0]['title']}"
        except Exception as e:
            return f"Erro ao atualizar: {e}"

    def delete_routine(routine_id: str) -> str:
        """Remove uma rotina e todo seu histórico.

        Args:
            routine_id: UUID da rotina a remover.
        """
        try:
            result = (
                sb.table("routines")
                .delete()
                .eq("id", routine_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                return "Rotina não encontrada."
            return f"Rotina removida: {result.data[0]['title']}"
        except Exception as e:
            return f"Erro ao remover: {e}"

    return [
        create_routine,
        list_routines,
        log_routine,
        get_today_routines,
        update_routine,
        delete_routine,
    ]
