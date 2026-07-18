import logging
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import hooks
from app.config import GEMINI_API_KEY, APP_DATA_DIR, AGENT_MODEL
from app.tools.system_metrics import check_system_metrics
from app.database.audit_log import save_audit_log

# Configuração do Logger do SDK
logger = logging.getLogger("google.antigravity")
logger.setLevel(logging.INFO)

# Definição dos Hooks de Ciclo de Vida do Google Antigravity SDK
@hooks.on_session_start
async def on_session_start():
    logger.info("[SESSION HOOK] Sessão de Orquestração Inicializada com Sucesso!")

@hooks.on_session_end
async def on_session_end():
    logger.info("[SESSION HOOK] Sessão de Orquestração Encerrada. Tracing concluído.")

@hooks.pre_turn
async def pre_turn_hook(data: str) -> types.HookResult:
    logger.info(f"[TURN HOOK - PRE] Prompt Interceptado: '{data}'")
    return types.HookResult(allow=True)

@hooks.post_turn
async def post_turn_hook(data: str):
    logger.info(f"[TURN HOOK - POST] Resposta Interceptada (Tamanho: {len(data)} caracteres)")


async def run_agent_orchestrator(session_id: str, prompt: str) -> dict:
    """
    Executa a sessão do Agente Google Antigravity, orquestrando ferramentas customizadas,
    subagentes de pesquisa e extraindo estatísticas de token e custos com ganchos de monitoramento.
    """
    # Configuração de capacidades do agente
    capabilities = types.CapabilitiesConfig(
        enable_subagents=True  # Habilita delegação automática de pesquisa para subagentes
    )

    # Configuração local do agente com o SDK
    config = LocalAgentConfig(
        model=AGENT_MODEL,
        app_data_dir=APP_DATA_DIR,
        api_key=GEMINI_API_KEY,
        capabilities=capabilities,
        tools=[check_system_metrics],
        hooks=[
            on_session_start,
            on_session_end,
            pre_turn_hook,
            post_turn_hook
        ]
    )

    total_turns = 0
    response_text = ""
    usage_data = {
        "prompt_token_count": 0,
        "candidates_token_count": 0,
        "thoughts_token_count": 0,
        "total_token_count": 0
    }

    # Inicializa o Agente dentro do ciclo de vida assíncrono (async with) do SDK
    async with Agent(config=config) as agent:
        total_turns += 1
        response = await agent.chat(prompt)
        response_text = await response.text()

        # Extrai os metadados de uso de tokens do barramento da conversa ativa
        try:
            total_usage = agent.conversation.total_usage
            if total_usage:
                usage_data = {
                    "prompt_token_count": getattr(total_usage, "prompt_token_count", 0),
                    "candidates_token_count": getattr(total_usage, "candidates_token_count", 0),
                    "thoughts_token_count": getattr(total_usage, "thoughts_token_count", 0),
                    "total_token_count": getattr(total_usage, "total_token_count", 0)
                }
        except Exception as e:
            logger.warning(f"Erro ao extrair metadados de tokens da conversa: {e}")

    # Grava o relatório de auditoria Markdown em disco e atualiza o índice
    save_audit_log(
        session_id=session_id,
        model=AGENT_MODEL,
        total_turns=total_turns,
        usage=usage_data
    )

    return {
        "session_id": session_id,
        "response": response_text,
        "usage": usage_data
    }
