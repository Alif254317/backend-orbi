import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import HOST, PORT
from agents.router import get_router
from api import agenda as agenda_api
from api import shopping as shopping_api
from api import finance as finance_api
from api import tasks as tasks_api
from api import routines as routines_api
from api import ideas as ideas_api

app = FastAPI(title="Arara AI Backend", version="0.1.0")
app.include_router(agenda_api.router)
app.include_router(shopping_api.router)
app.include_router(finance_api.router)
app.include_router(tasks_api.router)
app.include_router(routines_api.router)
app.include_router(ideas_api.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Available modules (will grow as we add plugins)
MODULES = [
    {
        "id": "general",
        "name": "Chat Geral",
        "description": "Converse com a Arara sobre qualquer assunto",
        "icon": "chat",
        "enabled": True,
    },
    {
        "id": "agenda",
        "name": "Agenda",
        "description": "Eventos, compromissos e lembretes",
        "icon": "calendar",
        "enabled": True,
    },
    {
        "id": "shopping",
        "name": "Lista de Compras",
        "description": "Itens para comprar e marcar como concluídos",
        "icon": "shopping_cart",
        "enabled": True,
    },
    {
        "id": "finance",
        "name": "Finanças",
        "description": "Controle de gastos, receitas e saldo",
        "icon": "account_balance_wallet",
        "enabled": True,
    },
    {
        "id": "tasks",
        "name": "Tarefas",
        "description": "To-do list com prioridades e prazos",
        "icon": "task_alt",
        "enabled": True,
    },
    {
        "id": "routines",
        "name": "Rotinas",
        "description": "Hábitos diários: remédios, água, exercício e mais",
        "icon": "repeat",
        "enabled": True,
    },
    {
        "id": "ideas",
        "name": "Ideias",
        "description": "Captura rápida de pensamentos, estruturada pela IA",
        "icon": "lightbulb",
        "enabled": True,
    },
]


class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_id: str
    context: dict | None = None


class ChatResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: dict | None = None


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/modules")
async def list_modules():
    return {"modules": MODULES}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        router = get_router(
            session_id=request.session_id,
            user_id=request.user_id,
        )

        response = router.run(request.message)

        content = response.content if response.content else ""

        return ChatResponse(
            success=True,
            data={"content": content},
        )
    except Exception as e:
        print(f"[Chat] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=ChatResponse(
                success=False,
                error={"message": str(e)},
            ).model_dump(),
        )


if __name__ == "__main__":
    print(f"Starting Arara AI Backend on {HOST}:{PORT}")
    uvicorn.run("app:app", host=HOST, port=PORT, reload=True)
