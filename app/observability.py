import logging
from typing import Any, Dict, Optional
from app.config import AGENT_MODEL

logger = logging.getLogger("google.antigravity.observability")

try:
    from langfuse import Langfuse
    langfuse_client = Langfuse(
        public_key="pk-lf-demo",
        secret_key="sk-lf-demo",
        host="http://localhost:3000",
    )
except Exception as e:
    logger.warning(f"Could not initialize Langfuse in orchestrator: {e}")
    langfuse_client = None


def _create_trace(
    name: str,
    session_id: Optional[str] = None,
    tags: Optional[list] = None,
    input_data: Optional[Any] = None,
    metadata: Optional[dict] = None
) -> Any:
    if not langfuse_client:
        return None
    try:
        if hasattr(langfuse_client, "trace"):
            return langfuse_client.trace(
                name=name,
                session_id=session_id,
                tags=tags,
                input=input_data,
                metadata=metadata
            )
        elif hasattr(langfuse_client, "start_observation"):
            return langfuse_client.start_observation(
                name=name,
                type="TRACE",
                session_id=session_id,
                tags=tags,
                input=input_data,
                metadata=metadata
            )
    except Exception as e:
        logger.warning(f"Error creating Langfuse trace: {e}")
    return None


class OrchestratorObservability:
    @staticmethod
    def start_agent_trace(session_id: str, prompt: str) -> Any:
        return _create_trace(
            name="antigravity_agent_session",
            session_id=session_id,
            tags=["google-antigravity-sdk", f"model:{AGENT_MODEL}", "orchestrator"],
            input_data={"prompt": prompt},
            metadata={"session_id": session_id, "model": AGENT_MODEL}
        )

    @staticmethod
    def record_hook_span(trace: Any, hook_name: str, event_data: Any) -> Any:
        if not trace:
            return None
        try:
            if hasattr(trace, "span"):
                span = trace.span(name=f"hook_{hook_name}", input={"event": event_data})
                if hasattr(span, "end"):
                    span.end()
                return span
        except Exception as e:
            logger.warning(f"Error recording hook span: {e}")
        return None

    @staticmethod
    def record_usage_and_cost(trace: Any, usage_data: Dict[str, Any], cost_usd: float):
        if not trace:
            return
        try:
            if hasattr(trace, "update"):
                trace.update(
                    output={"usage": usage_data, "cost_usd": cost_usd},
                    metadata={"usage": usage_data, "total_cost_usd": cost_usd}
                )
            if hasattr(trace, "score"):
                trace.score(name="estimated_cost_usd", value=cost_usd)
        except Exception as e:
            logger.warning(f"Error recording usage and cost: {e}")

    @staticmethod
    def flush():
        if langfuse_client and hasattr(langfuse_client, "flush"):
            try:
                langfuse_client.flush()
            except Exception:
                pass
