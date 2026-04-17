# Integração com o Agente Arara AI

Guia para sistemas externos conversarem com o agente Arara AI em nome de um usuário.

A Arara é um **roteador de agentes Agno**: o sistema externo envia uma mensagem em linguagem natural, o roteador classifica a intenção e entrega para o especialista certo (agenda, finanças, compras, tarefas, rotinas, ideias ou chat geral). Os dados ficam no Supabase do usuário e são acessíveis em nome dele.

---

## 1. Obter uma API Key

A chave é gerada pelo próprio usuário dentro do app Arara AI:

1. Abrir o app e logar na conta Supabase dele.
2. **Configurações → INTEGRAÇÕES → API Keys**.
3. Toque em **"Nova chave"**, dê um label (ex.: "Zapier", "Script Python") e confirme.
4. A chave aparece em tela no formato `ara_live_xxxxxxxx...`. Copie e guarde.

A chave pertence ao usuário que a criou — toda requisição feita com ela age **em nome dele**. Várias chaves podem coexistir. O usuário pode revogar qualquer uma pelo mesmo painel a qualquer momento.

---

## 2. Autenticação

Envie a chave no header `X-API-Key` em toda requisição:

```
X-API-Key: ara_live_AbC123XyZ...
```

Se a chave estiver ausente, inválida ou revogada, a resposta é `401 Unauthorized`.

> Alternativa: o header `Authorization: Bearer <supabase-jwt>` também é aceito, mas é destinado ao app oficial. Sistemas externos devem usar `X-API-Key`.

---

## 3. Endpoint: `POST /chat`

Única rota necessária para conversar com o agente.

**URL:** `https://<seu-host>/chat`

**Headers:**
```
Content-Type: application/json
X-API-Key: ara_live_...
```

**Body:**
```json
{
  "session_id": "identificador-da-conversa",
  "message": "texto do usuário",
  "context": { }
}
```

| Campo         | Tipo     | Obrigatório | Descrição                                                                 |
|---------------|----------|-------------|---------------------------------------------------------------------------|
| `session_id`  | string   | sim         | Identificador da conversa. O agente mantém contexto entre mensagens do mesmo `session_id`. Use UUID ou qualquer string estável. |
| `message`     | string   | sim         | Texto do usuário em linguagem natural.                                    |
| `context`     | object   | não         | Metadados opcionais passados ao agente (ex.: `recording_id`, `transcription`). |

**Resposta (200):**
```json
{
  "success": true,
  "data": {
    "content": "Registrei R$ 45,00 de almoço hoje."
  }
}
```

**Resposta de erro (500):**
```json
{
  "success": false,
  "error": { "message": "descrição do erro" }
}
```

**Códigos HTTP:**
- `200` — sucesso
- `401` — chave ausente, inválida ou revogada
- `500` — erro interno (agente, LLM ou Supabase)

---

## 4. Session ID — mantendo contexto

O `session_id` agrupa mensagens da mesma conversa. O agente lembra do histórico recente dentro de uma sessão. Regra prática:

- **Uma conversa por vez** → mesmo `session_id`.
- **Conversa nova** (tópico trocado, usuário reiniciou) → novo `session_id`.
- Não precisa criar a sessão antecipadamente. A primeira mensagem cria.

Exemplo: um integrador pode usar o ID da thread no Slack como `session_id`, ou um UUID gerado no início de cada sessão de chat no seu produto.

---

## 5. Exemplos

### cURL

```bash
curl -X POST https://seu-host/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ara_live_AbC123..." \
  -d '{
    "session_id": "sess-001",
    "message": "gastei 45 reais no almoço hoje"
  }'
```

### Python

```python
import requests

API_KEY = "ara_live_AbC123..."
BASE_URL = "https://seu-host"

def send_message(session_id: str, message: str) -> str:
    r = requests.post(
        f"{BASE_URL}/chat",
        headers={"X-API-Key": API_KEY},
        json={"session_id": session_id, "message": message},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(data.get("error", {}).get("message", "unknown"))
    return data["data"]["content"]

print(send_message("sess-001", "quanto gastei esse mês?"))
```

### Node.js / TypeScript

```ts
const API_KEY = process.env.ARARA_API_KEY!;
const BASE_URL = "https://seu-host";

async function sendMessage(sessionId: string, message: string): Promise<string> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  if (!data.success) throw new Error(data.error?.message ?? "unknown");
  return data.data.content;
}

console.log(await sendMessage("sess-001", "me lembra amanhã de ligar pro João"));
```

### n8n / Zapier

Configure uma requisição HTTP genérica:
- **Método:** POST
- **URL:** `https://seu-host/chat`
- **Headers:** `X-API-Key: ara_live_...`, `Content-Type: application/json`
- **Body:** `{"session_id": "{{$execution.id}}", "message": "{{$json.texto}}"}`

---

## 6. O que o agente consegue fazer

Basta mandar em linguagem natural — o roteador decide. Exemplos por módulo:

| Módulo    | Exemplos de mensagens                                                          |
|-----------|--------------------------------------------------------------------------------|
| Agenda    | "me lembra amanhã de ligar pro João", "o que tenho hoje?"                      |
| Compras   | "adiciona leite e ovos na lista", "o que tem na lista?"                        |
| Finanças  | "gastei 45 no almoço", "meu saldo desse mês"                                   |
| Tarefas   | "preciso entregar o relatório até sexta", "o que tenho pra fazer hoje?"        |
| Rotinas   | "tomar Losartana todo dia às 8h e 20h"                                         |
| Ideias    | "anota essa ideia: criar um app de receitas"                                   |
| Geral     | qualquer pergunta que não se encaixe acima                                     |

O agente responde em texto. As gravações no Supabase (criar evento, lançar despesa, etc.) acontecem automaticamente quando a mensagem pede.

---

## 7. Boas práticas

- **Timeout:** use pelo menos 60 segundos no cliente — o agente pode encadear várias chamadas ao LLM.
- **Idempotência:** não há hoje. Não retente o mesmo `session_id`+`message` em loop sem lógica, senão acumula duplicatas (ex.: dois eventos criados).
- **Armazenamento da chave:** nunca commite em repositório público. Use env vars / secrets manager.
- **Rotação:** para trocar uma chave, crie uma nova no app, atualize o sistema externo, só depois revogue a antiga.
- **Limite de escopo:** hoje uma chave dá acesso completo aos dados do usuário. Não a compartilhe.

---

## 8. Suporte

- Código-fonte do backend: https://github.com/Alif254317/backend-orbi
- Reportar bugs: abrir issue no repositório acima.
