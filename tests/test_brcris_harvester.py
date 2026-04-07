import src.ingestion.brcris_harvester as brcris


def test_candidate_urls_from_env(monkeypatch):
    monkeypatch.setenv("BRCRIS_API_URLS", "https://a/api/works, https://b/api/works")
    urls = brcris._candidate_urls()
    assert urls == ["https://a/api/works", "https://b/api/works"]


def test_fetch_remote_tries_multiple_endpoints(monkeypatch):
    calls = []

    def fake_fetch(url, limit, query=None):
        calls.append(url)
        if "fail" in url:
            raise RuntimeError("down")
        return [{"id": "ok", "title": "ok"}]

    monkeypatch.setattr(brcris, "_candidate_urls", lambda: ["https://fail/api/works", "https://ok/api/works"])
    monkeypatch.setattr(brcris, "_fetch_remote_from_url", fake_fetch)

    rows = brcris._fetch_remote(limit=5, query="fair")
    assert rows == [{"id": "ok", "title": "ok"}]
    assert calls == ["https://fail/api/works", "https://ok/api/works"]
