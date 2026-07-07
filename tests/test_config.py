import os
from agent_graph.config import Settings

def test_default_settings():
    """Verify that Settings class defaults load with correct fallback values."""
    # Instantiate Settings with an empty environment to test class defaults
    settings = Settings(_env_file=None, google_api_key="mock_key")
    
    # Assert default values defined in config.py
    assert settings.MODEL_SUPERVISOR == "gemini-2.5-pro"
    assert settings.MODEL_CODER == "gemini-2.5-flash"
    assert settings.MOCK_LLM is True
    assert settings.MAX_ITERATIONS == 15
    assert settings.PORT == 8000
