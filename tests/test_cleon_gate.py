import pytest
from unittest.mock import patch
from cleon_gate import CleonDynastyGate, evaluate_cleon_trip, cosine_similarity

def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v2)) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v3)) == 0.0

    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1, 2], [1]) == 0.0

def test_gate_1_dawn_filter():
    gate = CleonDynastyGate()

    # Valid motion signal
    res = gate.evaluate_trip("Front Doorbell Ring Motion Alert")
    assert res["gate_1_dawn"]["passed"] is True

    # Noise trigger without keywords
    res_noise = gate.evaluate_trip("System Heartbeat Ping")
    assert res_noise["gate_1_dawn"]["passed"] is False
    assert res_noise["action_taken"] == "SUPPRESSED_BY_DAWN"

def test_gate_2_and_3_friendly_identity(temp_env_setup):
    config = temp_env_setup

    # Mock known identity "Mom"
    with patch("cleon_gate.get_known_identities", return_value=[{"name": "Mom", "source": "test"}]):
        res = evaluate_cleon_trip("Mom arriving at front camera doorbell", config=config)
        assert res["gate_2_day"]["classification"] == "FRIENDLY_VERIFIED"
        assert res["gate_3_dusk"]["verdict"] == "SEALED_SILENT_GOLD"
        assert res["action_taken"] == "SEALED_SILENT_GOLD"

def test_gate_2_and_3_unrecognized_stranger(temp_env_setup):
    config = temp_env_setup

    with patch("cleon_gate.get_known_identities", return_value=[]), \
         patch("cleon_gate.trigger_alexa_alert") as mock_alexa, \
         patch("cleon_gate.send_telegram_alert") as mock_tg:

        res = evaluate_cleon_trip("Motion on Backporch Floodlight alert", config=config)
        assert res["gate_2_day"]["classification"] == "UNRECOGNIZED_ANOMALY"
        assert res["gate_3_dusk"]["verdict"] == "ACTIVE_DEFENSE_TRIGGERED"
        assert res["action_taken"] == "ACTIVE_DEFENSE_TRIGGERED"
        assert mock_alexa.called
        assert mock_tg.called

@pytest.fixture
def temp_env_setup(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_cleon.db")
    monkeypatch.setenv("MYCAM_DB_PATH", db_path)
    return {"storage_dir": str(tmp_path), "alexa_bridge_enabled": True}
