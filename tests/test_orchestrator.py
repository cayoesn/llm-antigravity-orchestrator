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


def test_audit_log_missing_index_and_exception_handling():
    """
    Testa caminhos alternativos de exceção no módulo audit_log.py para garantir 100% de cobertura.
    """
    audits_dir = os.path.join(APP_DATA_DIR, "audits")
    index_file = os.path.join(APP_DATA_DIR, "audit_index.json")
    
    # 1. Garante que index_file não existe e chama get_audit_index
    if os.path.exists(index_file):
        os.remove(index_file)
    assert audit_log.get_audit_index() == []
    
    # 2. Escreve JSON corrompido no arquivo de índice
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(index_file, "w", encoding="utf-8") as f:
        f.write("{invalid-json:")
        
    # get_audit_index() deve lidar com a exceção e retornar []
    assert audit_log.get_audit_index() == []
    
    # save_audit_log() deve tratar o arquivo corrompido, resetar para [] e salvar com sucesso
    filepath = audit_log.save_audit_log(
        session_id="test-corrupted-session",
        model="gemini-3.5-flash",
        total_turns=1,
        usage={"prompt_token_count": 10, "total_token_count": 20}
    )
    assert os.path.exists(filepath)
    assert len(audit_log.get_audit_index()) == 1


@pytest.mark.asyncio
async def test_orchestrator_token_extraction_exception(monkeypatch):
    """
    Testa o bloco do except na extração de tokens em orchestrator.py para alcançar 100% de cobertura.
    """
    import sys
    
    # Obtém as classes de Mock corretas diretamente do módulo injetado
    AgentClass = sys.modules["google.antigravity"].Agent
    ConversationClass = AgentClass().conversation.__class__
    
    # 1. Patch no __init__ de ConversationClass para não definir total_usage no __dict__ do objeto
    monkeypatch.setattr(ConversationClass, "__init__", lambda self: None)
    
    # 2. Patch do atributo total_usage na classe ConversationClass como uma propriedade que levanta exceção
    @property
    def broken_total_usage(self):
        raise AttributeError("Simulated conversation extraction failure")
        
    monkeypatch.setattr(ConversationClass, "total_usage", broken_total_usage, raising=False)
    
    session_id = "test-error-session-tokens"
    result = await run_agent_orchestrator(
        session_id=session_id,
        prompt="Olá"
    )
    
    # O orquestrador deve rodar com sucesso mesmo com a falha de extração, usando valores padrão de tokens zerados
    assert result["session_id"] == session_id
    assert result["usage"]["prompt_token_count"] == 0
    assert result["usage"]["total_token_count"] == 0


@pytest.mark.asyncio
async def test_api_chat_exception_handling(monkeypatch):
    """
    Testa o bloco try/except do endpoint /api/chat no main.py.
    """
    # Mock do run_agent_orchestrator para lançar um erro genérico
    async def mock_failed_orchestrator(*args, **kwargs):
        raise RuntimeError("Conexão simulada falhou!")
        
    monkeypatch.setattr("app.main.run_agent_orchestrator", mock_failed_orchestrator)
    
    response = client.post(
        "/api/chat",
        json={"prompt": "Disparar erro", "session_id": "test-err-session-api"}
    )
    assert response.status_code == 500
    assert "Erro interno" in response.json()["detail"]


def test_observability_coverage(monkeypatch):
    """
    Testa todas as rotas e exceções do módulo OrchestratorObservability para garantir 100% de cobertura.
    """
    from app.observability import OrchestratorObservability, _create_trace
    import app.observability as obs_mod

    class MockSpan:
        def end(self):
            pass

    class MockTrace:
        def span(self, name, input=None):
            return MockSpan()
        def update(self, output=None, metadata=None):
            pass
        def score(self, name, value):
            pass

    class MockLangfuse:
        def trace(self, **kwargs):
            return MockTrace()
        def start_observation(self, **kwargs):
            return MockTrace()
        def flush(self):
            pass

    monkeypatch.setattr(obs_mod, "langfuse_client", MockLangfuse())

    trace = OrchestratorObservability.start_agent_trace("session-obs-test", "Prompt de teste")
    assert trace is not None

    span = OrchestratorObservability.record_hook_span(trace, "test_hook", {"event": "start"})
    assert span is not None

    OrchestratorObservability.record_usage_and_cost(
        trace,
        {"prompt_token_count": 10, "candidates_token_count": 10, "thoughts_token_count": 0, "total_token_count": 20},
        0.00001
    )

    OrchestratorObservability.flush()

    # Testes com langfuse_client zerado / Nulo
    monkeypatch.setattr(obs_mod, "langfuse_client", None)
    assert _create_trace("test") is None
    assert OrchestratorObservability.record_hook_span(None, "hook", {}) is None
    OrchestratorObservability.record_usage_and_cost(None, {}, 0.0)


def test_audit_hash_chain_integrity_and_tamper_detection():
    """Valida encadeamento SHA-256 e detecção imediata de violação/adulteração."""
    # 1. Cria 3 blocos de auditoria em cadeia
    audit_log.save_audit_log("sess_1", "gemini-3.5-flash", 1, {"total_token_count": 100})
    audit_log.save_audit_log("sess_2", "gemini-3.5-flash", 2, {"total_token_count": 200})
    audit_log.save_audit_log("sess_3", "gemini-3.5-flash", 3, {"total_token_count": 300})

    # 2. Verifica integridade inicial
    is_valid, msg = audit_log.verify_audit_chain_integrity()
    assert is_valid is True
    assert "3 blocos de auditoria verificados" in msg

    # 3. Simula adulteração de custo no bloco do meio
    import json
    with open(audit_log.INDEX_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Forja o custo sem recomputar hash
    records[1]["total_cost_usd"] = 9999.99

    with open(audit_log.INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f)

    # 4. Verificação deve falhar e apontar violação
    is_valid_tampered, tamper_msg = audit_log.verify_audit_chain_integrity()
    assert is_valid_tampered is False
    assert "Adulteração detectada no bloco 1" in tamper_msg




