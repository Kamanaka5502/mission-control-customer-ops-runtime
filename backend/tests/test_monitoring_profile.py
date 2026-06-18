from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_monitoring_profile_returns_operational_shape():
    response = client.get("/ops/monitoring")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "mission-control-customer-ops-runtime"
    assert body["health"] in {"healthy", "degraded"}
    assert "database" in body
    assert "schema" in body
    assert "runtime_counts" in body
    assert "alerts" in body
    assert body["incident_handoff"]["correlation_id_required"] is True
    assert "/ops/monitoring" in body["incident_handoff"]["first_checks"]


def test_monitoring_profile_includes_outcome_and_lifecycle_counters():
    response = client.get("/ops/monitoring")

    assert response.status_code == 200
    counts = response.json()["runtime_counts"]
    assert set(counts["outcomes"].keys()) == {"ADMIT", "HOLD", "ESCALATE", "REFUSE"}
    assert isinstance(counts["lifecycle_statuses"], dict)
    assert isinstance(counts["total_requests"], int)
    assert isinstance(counts["total_audit_events"], int)


def test_metrics_endpoint_remains_available():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["service"] == "mission-control-customer-ops-runtime"
