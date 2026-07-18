import sys
from unittest.mock import MagicMock

# Criando as classes Mock do Google Antigravity SDK
class MockUsageMetadata:
    def __init__(self):
        self.prompt_token_count = 150
        self.candidates_token_count = 100
        self.thoughts_token_count = 50
        self.total_token_count = 300

class MockConversation:
    def __init__(self):
        self.total_usage = MockUsageMetadata()

class MockResponse:
    async def text(self):
        return "Olá! Sou o agente Google Antigravity de teste. Suas métricas de CPU estão em 25%."

class MockAgent:
    def __init__(self, config=None):
        self.config = config
        self.conversation = MockConversation()

    async def __aenter__(self):
        if self.config and getattr(self.config, "hooks", None):
            for hook in self.config.hooks:
                if getattr(hook, "__name__", "") == "on_session_start":
                    await hook()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.config and getattr(self.config, "hooks", None):
            for hook in self.config.hooks:
                if getattr(hook, "__name__", "") == "on_session_end":
                    await hook()
        return False

    async def chat(self, prompt: str):
        if self.config and getattr(self.config, "hooks", None):
            for hook in self.config.hooks:
                if getattr(hook, "__name__", "") == "pre_turn_hook":
                    await hook(prompt)
                    
        response = MockResponse()
        
        if self.config and getattr(self.config, "hooks", None):
            for hook in self.config.hooks:
                if getattr(hook, "__name__", "") == "post_turn_hook":
                    await hook(await response.text())
                    
        return response

# Classes Dummy de Configuração
class DummyLocalAgentConfig:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class DummyCapabilitiesConfig:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

# Mocks para decorações de Hooks
class DummyHooks:
    def on_session_start(self, f):
        f.__name__ = "on_session_start"
        return f
    def on_session_end(self, f):
        f.__name__ = "on_session_end"
        return f
    def pre_turn(self, f):
        f.__name__ = "pre_turn_hook"
        return f
    def post_turn(self, f):
        f.__name__ = "post_turn_hook"
        return f

# ==============================================================================
# INJEÇÃO E MOCKING GLOBAL (Executado IMEDIATAMENTE no carregamento do conftest.py)
# Isso garante que qualquer import 'google.antigravity' importará nossos Mocks,
# eliminando chamadas reais de rede e travamentos (hangs).
# ==============================================================================
mock_module = MagicMock()
mock_module.Agent = MockAgent
mock_module.LocalAgentConfig = DummyLocalAgentConfig
mock_module.types.CapabilitiesConfig = DummyCapabilitiesConfig
sys.modules["google.antigravity"] = mock_module

mock_hooks_module = MagicMock()
mock_hooks_module.hooks = DummyHooks()
sys.modules["google.antigravity.hooks"] = mock_hooks_module
