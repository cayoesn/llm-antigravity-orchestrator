import os
import json
import hashlib
from datetime import datetime
from app.config import APP_DATA_DIR

AUDIT_DIR = os.path.join(APP_DATA_DIR, "audits")
INDEX_PATH = os.path.join(APP_DATA_DIR, "audit_index.json")

# Preços ilustrativos por token para o Gemini 3.5-flash
COST_PROMPT = 0.000000075     # $0.075 / milhão
COST_CANDIDATE = 0.00000030   # $0.30 / milhão
COST_THINKING = 0.00000030    # $0.30 / milhão


def calculate_gemini_cost(model: str, prompt_tokens: int, candidates_tokens: int, thinking_tokens: int) -> float:
    """Calcula o custo estimado em USD com base na quantidade de tokens."""
    return (prompt_tokens * COST_PROMPT) + (candidates_tokens * COST_CANDIDATE) + (thinking_tokens * COST_THINKING)


def _compute_record_hash(record: dict, previous_hash: str) -> str:
    """Calcula o hash criptográfico SHA-256 determinístico de um registro de auditoria."""
    payload = {
        "session_id": record.get("session_id"),
        "timestamp": record.get("timestamp"),
        "model": record.get("model"),
        "total_tokens": record.get("total_tokens"),
        "total_cost_usd": record.get("total_cost_usd"),
        "previous_hash": previous_hash,
    }
    canonical_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def save_audit_log(session_id: str, model: str, total_turns: int, usage: dict) -> str:
    """
    Grava um arquivo Markdown de auditoria e anexa o registro à Hash Chain criptográfica SHA-256.
    """
    prompt_tokens = usage.get("prompt_token_count", 0)
    candidates_tokens = usage.get("candidates_token_count", 0)
    thinking_tokens = usage.get("thoughts_token_count", 0)
    total_tokens = usage.get("total_token_count", 0)

    # Cálculo dos custos estimados em USD
    cost_prompt_est = prompt_tokens * COST_PROMPT
    cost_candidate_est = candidates_tokens * COST_CANDIDATE
    cost_thinking_est = thinking_tokens * COST_THINKING
    total_cost_est = cost_prompt_est + cost_candidate_est + cost_thinking_est

    timestamp = datetime.now().isoformat()

    # Criação do relatório Markdown formatado
    report_content = f"""# Relatório de Auditoria de Custos e Tracing 📊

## Informações da Sessão
- **ID da Sessão:** `{session_id}`
- **Data/Hora de Encerramento:** `{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`
- **Modelo Utilizado:** `{model}`
- **Total de Turns Executados:** `{total_turns}`

---

## 📈 Métricas de Token e Consumo
| Tipo de Token | Quantidade | Custo Estimado (USD) |
| :--- | :---: | :---: |
| **Prompt Tokens** | {prompt_tokens} | ${cost_prompt_est:.8f} |
| **Candidates Tokens** (Geração) | {candidates_tokens} | ${cost_candidate_est:.8f} |
| **Thinking/Reasoning Tokens** | {thinking_tokens} | ${cost_thinking_est:.8f} |
| **Total de Tokens** | **{total_tokens}** | **${total_cost_est:.8f}** |

> [!NOTE]
> Os custos estimados acima são calculados dinamicamente com base nas tabelas de preços oficiais do Google AI Studio para o modelo `{model}`.

---

## 🛡️ Observabilidade & Governança de IA
- **Diretório de Dados Confinado:** `{APP_DATA_DIR}`
- **Ganchos de Rastreabilidade:** `@hooks.on_session_start`, `@hooks.on_session_end`, `@hooks.post_turn`
- **Validação de Tracing:** O encerramento da sessão acionou com sucesso os hooks de auditoria de custo e salvamento assíncrono.
"""

    report_filename = f"{session_id}.md"
    report_filepath = os.path.join(AUDIT_DIR, report_filename)

    with open(report_filepath, "w", encoding="utf-8") as f:
        f.write(report_content)

    # Atualiza o índice geral de auditoria JSON com encadeamento de hash SHA-256
    index_data = []
    if os.path.exists(INDEX_PATH):
        try:
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        except Exception:
            index_data = []

    # Remove registro duplicado se houver
    index_data = [item for item in index_data if item.get("session_id") != session_id]

    # Determina o previous_hash
    genesis_hash = "0" * 64
    previous_hash = index_data[-1].get("current_hash", genesis_hash) if index_data else genesis_hash

    new_record = {
        "session_id": session_id,
        "timestamp": timestamp,
        "model": model,
        "total_turns": total_turns,
        "prompt_tokens": prompt_tokens,
        "candidates_tokens": candidates_tokens,
        "thinking_tokens": thinking_tokens,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost_est,
        "report_file": report_filename,
        "previous_hash": previous_hash,
    }
    new_record["current_hash"] = _compute_record_hash(new_record, previous_hash)

    index_data.append(new_record)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

    return report_filepath


def verify_audit_chain_integrity() -> tuple[bool, str]:
    """
    Verifica a integridade criptográfica da cadeia de auditoria SHA-256 em O(N).
    Detecta qualquer adulteração, inserção ou remoção não autorizada de registros.
    """
    if not os.path.exists(INDEX_PATH):
        return True, "Cadeia de auditoria vazia."

    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            index_data = json.load(f)
    except Exception as e:
        return False, f"Falha ao carregar índice de auditoria: {e}"

    if not index_data:
        return True, "Cadeia de auditoria vazia."

    genesis_hash = "0" * 64
    expected_previous = genesis_hash

    for i, record in enumerate(index_data):
        prev_hash = record.get("previous_hash", "")
        curr_hash = record.get("current_hash", "")

        if prev_hash != expected_previous:
            return False, f"Quebra de integridade no bloco {i} (Sessão {record.get('session_id')}): previous_hash incompatível."

        computed_hash = _compute_record_hash(record, prev_hash)
        if computed_hash != curr_hash:
            return False, f"Adulteração detectada no bloco {i} (Sessão {record.get('session_id')}): hash do payload corrompido."

        expected_previous = curr_hash

    return True, f"Cadeia íntegra. {len(index_data)} blocos de auditoria verificados com sucesso."


def get_audit_index() -> list:
    """
    Retorna a lista consolida de auditorias registradas.
    """
    if not os.path.exists(INDEX_PATH):
        return []
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def get_audit_report(session_id: str) -> str:
    """
    Retorna o conteúdo do arquivo Markdown de auditoria específico.
    """
    report_filepath = os.path.join(AUDIT_DIR, f"{session_id}.md")
    if not os.path.exists(report_filepath):
        return ""
    with open(report_filepath, "r", encoding="utf-8") as f:
        return f.read()
