import pytest
from src.agents.generator_agent.message_generator import generate_retention_message


def test_generate_retention_message_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        generate_retention_message(persona=None, recommended_action="discount_10")
