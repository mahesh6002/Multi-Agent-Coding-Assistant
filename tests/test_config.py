import os
from agent_graph.config import settings

def test_default_settings():
    """Verify that settings load with correct defaults."""
    assert settings.MODEL_SUPERVISOR == "gemini-2.5-pro"
    assert settings.MODEL_CODER == "gemini-2.5-flash"
    assert settings.MOCK_LLM is True
    assert settings.MAX_ITERATIONS == 15
    assert settings.PORT == 8000
