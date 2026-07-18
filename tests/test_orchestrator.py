import os
import shutil
import pytest
from fastapi.testclient import TestClient
from app.config import APP_DATA_DIR
from app.main import app
from app.tools.system_metrics import check_system_metrics
from app.database import audit_log
from app.orchestrator import run_agent_orchestrator

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def clean_test_environment():
    """
    Garante que a pasta de testes de auditoria esteja limpa antes e depois de cada teste.
    """
    audits_dir = os.path.join(APP_DATA_DIR, "audits")
    index_file = os.path.join(APP_DATA_DIR, "audit_index.json")
    
    # Limpa antes do teste
    if os.path.exists(audits_dir):
        shutil.rmtree(audits_dir)
    if os.path.exists(index_file):
        os.remove(index_file)
        
    os.makedirs(audits_dir, exist_ok=True)
    
    yield
    
    # Limpa após o teste
    if os.path.exists(audits_dir):
        shutil.rmtree(audits_dir)
    if os.path.exists(index_file):
        os.remove(index_file)


def test_system_metrics_tool():
    """
    Verifica se a ferramenta customizada de infraestrutura gera strings válidas.
    """
    result = check_system_metrics()
    assert "INFRASTRUCTURE PERFORMANCE REPORT" in result
    assert "Consumo de CPU:" in result
    assert "Consumo de Memória RAM:" in result


def test_audit_log_database():
    """
    Testa a gravação, leitura de relatórios markdown e consulta do índice geral.
    """
    session_id = "test-session-123"
    usage_mock = {
        "prompt_token_count": 100,
        "candidates_token_count": 50,
        "thoughts_token_count": 20,
        "total_token_count": 170
    }
    
    # Grava auditoria
    filepath = audit_log.save_audit_log(
        session_id=session_id,
        model="gemini-3.5-flash",
        total_turns=1,
        usage=usage_mock
    )
    
    assert os.path.exists(filepath)
    
    # Lê relatório markdown
    report = audit_log.get_audit_report(session_id)
    assert f"ID da Sessão:** `{session_id}`" in report
    assert "Prompt Tokens" in report
    assert "170" in report
    
    # Lista índice
    index = audit_log.get_audit_index()
    assert len(index) == 1
    assert index[0]["session_id"] == session_id
    assert index[0]["total_tokens"] == 170
    assert index[0]["total_cost_usd"] > 0.0


@pytest.mark.asyncio
async def test_run_agent_orchestrator():
    """
    Verifica a execução integrada do orquestrador do agente Google Antigravity.
    """
    session_id = "test-orchestrator-session"
    result = await run_agent_orchestrator(
        session_id=session_id,
        prompt="Como está a saúde da nossa infraestrutura?"
    )
    
    assert result["session_id"] == session_id
    assert "Olá! Sou o agente" in result["response"]
    assert result["usage"]["prompt_token_count"] == 150
    assert result["usage"]["total_token_count"] == 300


def test_api_health_check_endpoint():
    """
    Valida a rota de status básico da API.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["service"] == "llm-antigravity-orchestrator"


def test_api_chat_flow_endpoint():
    """
    Valida a chamada ao endpoint de chat integrado com o orquestrador do agente.
    """
    response = client.post(
        "/api/chat",
        json={"prompt": "Quais as métricas do cluster?", "session_id": "api-session-test"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "api-session-test"
    assert "Olá! Sou o agente" in data["response"]
    assert data["usage"]["total_token_count"] == 300


def test_api_list_audits_endpoint():
    """
    Valida a listagem do histórico de auditorias via API.
    """
    # Cria uma auditoria mockada para popular a API
    audit_log.save_audit_log(
        session_id="session-xyz",
        model="gemini-3.5-flash",
        total_turns=2,
        usage={"prompt_token_count": 50, "candidates_token_count": 50, "thoughts_token_count": 0, "total_token_count": 100}
    )
    
    response = client.get("/api/audits")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["session_id"] == "session-xyz"


def test_api_view_audit_report_endpoint():
    """
    Valida a leitura do relatório individual markdown via rota da API.
    """
    session_id = "session-abc"
    audit_log.save_audit_log(
        session_id=session_id,
        model="gemini-3.5-flash",
        total_turns=1,
        usage={"prompt_token_count": 80, "candidates_token_count": 40, "thoughts_token_count": 10, "total_token_count": 130}
    )
    
    # Rota válida
    response = client.get(f"/api/audits/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert "# Relatório de Auditoria" in data["markdown_report"]
    
    # Rota inválida (não existente)
    response_err = client.get("/api/audits/non-existent-session")
    assert response_err.status_code == 404
