import pytest
from fastapi.testclient import TestClient

from src.api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # runs the lifespan: trains the model
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["trained_on"] >= 100


def test_predict_phishing_and_legitimate(client):
    r = client.post("/predict", json={"urls": ["http://paypal-login-verify.test/confirm",
                                               "https://www.wikipedia.org"]})
    assert r.status_code == 200
    phishing, legit = r.json()
    assert phishing["label"] == 1 and legit["label"] == 0
    assert 0.0 <= phishing["probability"] <= 1.0


@pytest.mark.parametrize("payload", [{}, {"urls": []}, {"urls": "http://a.com"},
                                     {"urls": ["x"] * 101}])
def test_predict_rejects_invalid_input(client, payload):
    assert client.post("/predict", json=payload).status_code == 422
