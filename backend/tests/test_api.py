import pytest
from fastapi.testclient import TestClient

from get_the_notes import api
from get_the_notes.settings import settings


class FakeQueue:
    def __init__(self):
        self.calls = []

    def enqueue(self, func, *args, **kwargs):
        self.calls.append((func, args, kwargs))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    queue = FakeQueue()
    api.app.dependency_overrides[api.get_queue] = lambda: queue
    yield TestClient(api.app), queue
    api.app.dependency_overrides.clear()


def test_upload_enqueues_job(client, tmp_path):
    c, queue = client
    r = c.post("/api/jobs", files={"file": ("My Song.mp3", b"fake-bytes", "audio/mpeg")})
    assert r.status_code == 201
    job_id = r.json()["id"]
    assert (tmp_path / "jobs" / job_id / "input.mp3").read_bytes() == b"fake-bytes"
    func, args, kwargs = queue.calls[0]
    assert func == "get_the_notes.worker.process_job"
    assert args == (job_id,) and kwargs["job_id"] == job_id


def test_upload_rejects_wrong_type(client):
    c, _ = client
    r = c.post("/api/jobs", files={"file": ("notes.txt", b"x", "text/plain")})
    assert r.status_code == 415


def test_upload_rejects_too_large(client, monkeypatch, tmp_path):
    c, _ = client
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    r = c.post("/api/jobs", files={"file": ("big.wav", b"0" * (2 * 1024 * 1024), "audio/wav")})
    assert r.status_code == 413
    assert list((tmp_path / "jobs").iterdir()) == []


def test_files_are_whitelisted(client, tmp_path):
    c, _ = client
    job_id = c.post("/api/jobs", files={"file": ("a.wav", b"x", "audio/wav")}).json()["id"]
    assert c.get(f"/api/jobs/{job_id}/files/meta.json").status_code == 404
    assert c.get(f"/api/jobs/{job_id}/files/video.mp4").status_code == 404
    (tmp_path / "jobs" / job_id / "notes.json").write_text("{}")
    r = c.get(f"/api/jobs/{job_id}/files/notes.json?download=1")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert c.get("/api/jobs/../files/notes.json").status_code == 404
