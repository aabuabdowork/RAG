import os

os.environ.update(RATE_LIMIT_ASK="3/minute", MAX_UPLOAD_MB="1")

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.dependencies import get_container, limiter
from src.application.use_cases.delete_document import DeleteDocumentUseCase
from src.application.use_cases.metrics_report import MetricsReportUseCase
from src.application.use_cases.upload_document import UploadDocumentUseCase
from src.core.config import settings
from src.domain.entities import Answer, Retrieval, SearchResult
from src.domain.exceptions import BudgetExceededError, ServiceUnavailableError

os.environ["LANGSMITH_TRACING"] = "false"

KEY = {"X-API-Key": "test-key"}
SOURCE = SearchResult("1,500 SAR allowance", 0.9, "HR", "policy.pdf", 2, 1, 0.8)
PDF = b"%PDF-1.4 fake"


class Stub:
    def __init__(self, result):
        self.result = result

    def execute(self, *args):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class Memory:
    def __init__(self):
        self.items = {}

    def record(self, event, **fields):
        self.items.setdefault("events", []).append({"event": event, "request_id": "t", "time": "T00:00:00Z", **fields})

    def events(self):
        return self.items.get("events", [])

    def get(self, department, file_name):
        return next((d for d in self.items.values() if getattr(d, "key", None) == f"{department}/{file_name}"), None)

    def list(self, status=None):
        return [d for d in self.items.values() if hasattr(d, "key") and status in (None, d.status)]

    def save(self, document):
        self.items[document.id] = document

    def delete(self, document_id):
        self.items.pop(document_id, None)

    def upload(self, path, data):
        pass

    def delete_document(self, document_id):
        return 1


class FakeContainer:
    def __init__(self):
        self.metrics = Memory()
        self.repository = Memory()
        self.answer = Answer("It is 1,500 SAR. [HR/policy.pdf, p.2]", [SOURCE], True, ["q"], {"answer": 9})
        self.indexed = 0

    def ask(self, rerank, multi_query):
        return Stub(self.answer)

    def search(self, rerank, multi_query):
        return Stub(Retrieval(["q"], [SOURCE]))

    def upload(self):
        return UploadDocumentUseCase(self.repository, self.repository)

    def delete(self):
        return DeleteDocumentUseCase(self.repository, self.repository, self.repository)

    def stats(self):
        return MetricsReportUseCase(self.metrics, "model")

    def index_pending(self):
        self.indexed += 1
        return {}


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr("src.api.dependencies.settings", replace(settings, api_keys=("test-key",)))
    fake = FakeContainer()
    app.dependency_overrides[get_container] = lambda: fake
    limiter.reset()
    yield TestClient(app), fake
    app.dependency_overrides.clear()


def ask(client, body=None, headers=KEY):
    return client.post("/ask", json=body or {"query": "allowance?"}, headers=headers)


def test_health_is_public(setup):
    client, _ = setup
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}])
def test_protected_routes_need_a_valid_key(setup, headers):
    client, _ = setup
    assert ask(client, headers=headers).status_code == 401


def test_ask_returns_answer_sources_and_request_id(setup):
    client, fake = setup
    response = ask(client)
    body = response.json()
    assert response.status_code == 200
    assert body["found"] and body["sources"][0]["page"] == 2
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert fake.metrics.events()[-1]["event"] == "ask"


def test_not_found_hides_sources(setup):
    client, fake = setup
    fake.answer = Answer("I couldn't find this in the documents.", [SOURCE], False)
    body = ask(client).json()
    assert not body["found"] and body["sources"] == []


@pytest.mark.parametrize(
    "body",
    [{"query": ""}, {"query": "x", "top_k": 999}, {"query": "x", "department": "SALES"}, {"query": "x" * 2001}],
)
def test_invalid_input_is_rejected(setup, body):
    client, _ = setup
    assert ask(client, body).status_code == 422


@pytest.mark.parametrize(
    "error, status",
    [
        (BudgetExceededError("Question is 301 tokens"), 422),
        (ServiceUnavailableError("LLM", TimeoutError()), 503),
        (RuntimeError("boom"), 500),
    ],
)
def test_errors_map_to_http_status(setup, error, status):
    client, fake = setup
    fake.answer = error
    response = ask(client)
    assert response.status_code == status
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_rate_limit_returns_429_with_retry_after(setup):
    client, _ = setup
    codes = [ask(client).status_code for _ in range(4)]
    response = ask(client)
    assert codes == [200, 200, 200, 429]
    assert response.status_code == 429 and response.headers["Retry-After"] == "60"


def test_rate_limit_is_per_api_key(setup, monkeypatch):
    client, _ = setup
    monkeypatch.setattr("src.api.dependencies.settings", type("S", (), {"api_keys": ("test-key", "other")})())
    for _ in range(3):
        ask(client)
    assert ask(client).status_code == 429
    assert ask(client, headers={"X-API-Key": "other"}).status_code == 200


@pytest.mark.parametrize(
    "name, data, status",
    [("notes.txt", PDF, 415), ("fake.pdf", b"hello", 415), ("big.pdf", PDF + b"0" * 1024 * 1024, 413)],
    ids=["not-pdf-name", "not-pdf-content", "too-large"],
)
def test_upload_validation(setup, name, data, status):
    client, _ = setup
    response = client.post("/documents", data={"department": "HR"}, files={"file": (name, data)}, headers=KEY)
    assert response.status_code == status


def test_document_lifecycle(setup):
    client, fake = setup
    upload = lambda: client.post(
        "/documents", data={"department": "hr"}, files={"file": ("../../policy.pdf", PDF)}, headers=KEY
    )
    first, second = upload(), upload()
    assert first.status_code == 202 and first.json()["result"] == "uploaded"
    assert first.json()["document"] == "HR/policy.pdf"
    assert second.json()["result"] == "skipped" and fake.indexed == 1

    assert client.get("/documents", headers=KEY).json()[0]["status"] == "pending"
    assert client.get("/documents/HR/policy.pdf", headers=KEY).json()["file_name"] == "policy.pdf"
    assert client.delete("/documents/HR/policy.pdf", headers=KEY).json() == {"result": "deleted (1 points)"}
    assert client.get("/documents/HR/policy.pdf", headers=KEY).status_code == 404


def test_stats_reports_requests(setup):
    client, _ = setup
    ask(client)
    body = client.get("/stats", headers=KEY).json()
    assert body["totals"]["ask"]["requests"] == 1
    assert body["requests"][-1]["channel"] == "api"
