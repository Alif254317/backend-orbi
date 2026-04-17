import json
from typing import Callable

import httpx

from config import LLM_MODEL, LLM_BASE_URL, OPENAI_API_KEY
from tools.supabase_client import get_supabase


VALID_CATEGORIES = {
    "project", "insight", "question", "todo-candidate", "reference", "other"
}


STRUCTURE_PROMPT = """Você recebe um texto bruto (pensamento solto, transcrição de áudio
ou ideia rápida) e deve estruturá-lo em um card.

Responda APENAS com JSON válido no formato:
{
  "title": "Título curto e descritivo (máx 60 chars)",
  "content": "Resumo estruturado em 1-3 parágrafos curtos. Mantenha a essência do que foi dito, sem inventar.",
  "tags": ["tag1", "tag2", "tag3"],
  "category": "project" | "insight" | "question" | "todo-candidate" | "reference" | "other"
}

Regras:
- O título deve capturar a essência em poucas palavras
- O content deve ser claro e organizado, mas fiel ao original
- Tags: 2-5 palavras-chave em lowercase, sem espaços (use hífen)
- Category: escolha a mais apropriada
  - project: ideia de produto/negócio/sistema a construir
  - insight: reflexão, aprendizado, observação
  - question: dúvida ou tópico a investigar
  - todo-candidate: algo a fazer em breve
  - reference: informação, link, pessoa, fato a lembrar
  - other: não se encaixa nas anteriores
- NUNCA adicione informação que não está no texto original
- Responda em português brasileiro

Texto bruto:
"""


def structure_idea(raw_text: str) -> dict:
    """Call LLM to structure raw text into idea card format.
    Returns dict with keys: title, content, tags, category.
    """
    if not raw_text or not raw_text.strip():
        return {
            "title": "Ideia vazia",
            "content": raw_text,
            "tags": [],
            "category": "other",
        }

    try:
        response = httpx.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "user", "content": STRUCTURE_PROMPT + raw_text},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        content_str = data["choices"][0]["message"]["content"]
        parsed = json.loads(content_str)

        # Validate
        title = (parsed.get("title") or "Ideia").strip()[:80]
        content = (parsed.get("content") or raw_text).strip()
        tags = [t.strip().lower() for t in (parsed.get("tags") or []) if isinstance(t, str)][:5]
        category = parsed.get("category") or "other"
        if category not in VALID_CATEGORIES:
            category = "other"

        return {
            "title": title,
            "content": content,
            "tags": tags,
            "category": category,
        }
    except Exception as e:
        print(f"[ideas] structure failed: {e}")
        return {
            "title": raw_text[:60].strip() or "Ideia",
            "content": raw_text,
            "tags": [],
            "category": "other",
        }


def build_ideas_tools(user_id: str) -> list[Callable]:
    """Build ideas tools bound to a specific user_id."""
    sb = get_supabase()

    def capture_idea(raw_text: str, source: str = "text") -> str:
        """Captura uma ideia bruta e estrutura em um card com IA.

        Args:
            raw_text: Texto bruto da ideia (transcrição ou digitado).
            source: Origem — 'text' (padrão) ou 'voice'.
        """
        if not raw_text or not raw_text.strip():
            return "Erro: texto vazio."

        if source not in ("text", "voice"):
            source = "text"

        structured = structure_idea(raw_text)
        data = {
            "user_id": user_id,
            "title": structured["title"],
            "content": structured["content"],
            "raw_text": raw_text,
            "tags": structured["tags"],
            "category": structured["category"],
            "source": source,
        }
        try:
            result = sb.table("ideas").insert(data).execute()
            idea = result.data[0]
            tags_str = ", ".join(idea["tags"]) if idea["tags"] else "—"
            return f"Ideia capturada: \"{idea['title']}\" [{idea['category']}] tags: {tags_str} id={idea['id']}"
        except Exception as e:
            return f"Erro ao salvar ideia: {e}"

    def list_ideas(category: str = "", tag: str = "", archived: bool = False, limit: int = 20) -> str:
        """Lista as ideias do usuário.

        Args:
            category: Filtrar por categoria (project, insight, question, todo-candidate, reference, other).
            tag: Filtrar por uma tag específica.
            archived: Se True, mostra arquivadas.
            limit: Máximo de resultados (padrão 20).
        """
        try:
            q = (
                sb.table("ideas")
                .select("id, title, category, tags, created_at")
                .eq("user_id", user_id)
                .eq("is_archived", archived)
            )
            if category and category in VALID_CATEGORIES:
                q = q.eq("category", category)
            if tag:
                q = q.contains("tags", [tag.strip().lower()])
            result = q.order("created_at", desc=True).limit(limit).execute()

            if not result.data:
                return "Nenhuma ideia encontrada."

            lines = [f"{len(result.data)} ideia(s):"]
            for i in result.data:
                tags = " #".join(i.get("tags") or [])
                tag_str = f" #{tags}" if tags else ""
                lines.append(f"  [{i['category']}] {i['title']}{tag_str} (id={i['id']})")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro ao listar: {e}"

    def update_idea(
        idea_id: str,
        title: str = "",
        content: str = "",
        tags: str = "",
        category: str = "",
    ) -> str:
        """Atualiza uma ideia existente.

        Args:
            idea_id: UUID da ideia.
            title: Novo título (opcional).
            content: Novo conteúdo (opcional).
            tags: Novas tags separadas por vírgula (opcional).
            category: Nova categoria (opcional).
        """
        updates = {}
        if title:
            updates["title"] = title
        if content:
            updates["content"] = content
        if tags:
            updates["tags"] = [t.strip().lower() for t in tags.split(",") if t.strip()]
        if category and category in VALID_CATEGORIES:
            updates["category"] = category

        if not updates:
            return "Nenhuma alteração informada."
        try:
            result = (
                sb.table("ideas")
                .update(updates)
                .eq("id", idea_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                return "Ideia não encontrada."
            return f"Ideia atualizada: {result.data[0]['title']}"
        except Exception as e:
            return f"Erro ao atualizar: {e}"

    def archive_idea(idea_id: str) -> str:
        """Arquiva uma ideia (não deleta, só esconde).

        Args:
            idea_id: UUID da ideia.
        """
        try:
            result = (
                sb.table("ideas")
                .update({"is_archived": True})
                .eq("id", idea_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                return "Ideia não encontrada."
            return "Ideia arquivada."
        except Exception as e:
            return f"Erro: {e}"

    def delete_idea(idea_id: str) -> str:
        """Remove permanentemente uma ideia.

        Args:
            idea_id: UUID da ideia.
        """
        try:
            result = (
                sb.table("ideas")
                .delete()
                .eq("id", idea_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                return "Ideia não encontrada."
            return f"Ideia removida: {result.data[0]['title']}"
        except Exception as e:
            return f"Erro: {e}"

    return [capture_idea, list_ideas, update_idea, archive_idea, delete_idea]
