import os

# Configurações básicas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Chave de API do Gemini para o Google Antigravity SDK
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Caminho absoluto para persistência de dados do agente e logs de auditoria
APP_DATA_DIR = os.getenv(
    "APP_DATA_DIR",
    os.path.join(BASE_DIR, "app_data")
)

# Modelo padrão do agente do SDK
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-3.5-flash")

# Garante que o diretório de dados existe
os.makedirs(APP_DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(APP_DATA_DIR, "audits"), exist_ok=True)
