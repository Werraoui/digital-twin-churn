import pytest
from src.agents.prediction_agent.predict import predict_churn


def test_predict_churn_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        predict_churn(persona=None)
