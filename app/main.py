import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.orchestrator import run_agent_orchestrator
from app.database.audit_log import get_audit_index, get_audit_report

app = FastAPI(
    title="Google Antigravity Multi-Agent Orchestrator 🌐",
    description="Engine avançada de orquestração multi-agente e auditoria de tokens construída sobre o Google Antigravity SDK.",
    version="1.0.0"
)


class ChatRequest(BaseModel):
    prompt: str = Field(..., description="Prompt a ser enviado para o orquestrador de agentes.")
    session_id: str = Field(default=None, description="ID da sessão opcional. Se não enviado, um novo UUID será gerado.")


@app.get("/")
async def health_check():
    return {
        "status": "HEALTHY",
        "service": "llm-antigravity-orchestrator",
        "sdk": "Google Antigravity (AGY) SDK",
        "endpoints": {
            "chat": "POST /api/chat",
            "audits_list": "GET /api/audits",
            "audit_detail": "GET /api/audits/{session_id}"
        }
    }


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Submete uma instrução para o orquestrador.
    Ele executará a lógica do Google Antigravity Agent, ferramentas, subagentes e retornará a resposta consolidada
    junto com a auditoria de custos e consumo de tokens detalhados.
    """
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        result = await run_agent_orchestrator(session_id=session_id, prompt=request.prompt)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno durante a execução da orquestração: {str(e)}"
        )


@app.get("/api/audits")
async def list_audits_endpoint():
    """
    Retorna a lista consolida de relatórios de auditorias e tracing de custos gravados.
    """
    return get_audit_index()


@app.get("/api/audits/{session_id}")
async def view_audit_report_endpoint(session_id: str):
    """
    Retorna o relatório em formato Markdown de uma auditoria específica para visualização detalhada.
    """
    report = get_audit_report(session_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Relatório de auditoria para a sessão '{session_id}' não encontrado."
        )
    return {
        "session_id": session_id,
        "markdown_report": report
    }
