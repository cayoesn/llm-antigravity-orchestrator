FROM python:3.12-slim

WORKDIR /app

# Instala dependências de sistema necessárias
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia arquivos de definição de dependências e código da aplicação
COPY pyproject.toml ./
COPY app/ ./app/
COPY tests/ ./tests/

# Instala dependências via pip localmente para garantir velocidade e estabilidade
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    httpx \
    google-antigravity \
    pytest \
    pytest-cov \
    pytest-asyncio

# Porta padrão exposta pelo container do orquestrador
EXPOSE 8000

# Comando padrão de inicialização (pode ser sobrescrito para rodar testes)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
