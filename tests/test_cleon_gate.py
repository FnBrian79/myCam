import pytest
from cleon_gate import cosine_similarity, CleonDynastyGate, evaluate_cleon_trip

def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v2), 0.001) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v3), 0.001) == 0.0

    assert cosine_similarity(None, v1) == 0.0
    assert cosine_similarity([], v1) == 0.0

def test_cleon_gate_1_dawn_filtering():
    gate = CleonDynastyGate()

    # Valid motion signal
    res_valid = gate.evaluate_trip("Ring Doorbell Motion Detected")
    assert res_valid["gate_1_dawn"]["passed"] is True

    # Empty phantom digital noise
    res_noise = gate.evaluate_trip("System Background Sync Complete")
    assert res_noise["gate_1_dawn"]["passed"] is False
    assert res_noise["action_taken"] == "SUPPRESSED_BY_DAWN"

def test_cleon_gate_friendly_vs_unrecognized(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_cleon.db")
    monkeypatch.setenv("MYCAM_DB_PATH", db_file)
    config = {"storage_dir": str(tmp_path / "captures"), "alexa_bridge_enabled": False}

    from storage import insert_known_identity
    insert_known_identity("id_mom", "Mom", "test", "hash_mom_1", "/path/mom.jpg", {}, config=config)

    # Trip mentioning registered identity Mom and valid signal camera
    res_friendly = evaluate_cleon_trip("Mom arriving at Front Doorbell Camera", config=config)
    assert res_friendly["gate_1_dawn"]["passed"] is True
    assert res_friendly["gate_2_day"]["classification"] == "FRIENDLY_VERIFIED"
    assert res_friendly["action_taken"] == "SEALED_SILENT_GOLD"

    # Trip with unknown visitor and valid signal motion
    res_unknown = evaluate_cleon_trip("Motion detected on Backporch Camera", config=config)
    assert res_unknown["gate_1_dawn"]["passed"] is True
    assert res_unknown["gate_2_day"]["classification"] == "UNRECOGNIZED_ANOMALY"
    assert res_unknown["action_taken"] == "ACTIVE_DEFENSE_TRIGGERED"
