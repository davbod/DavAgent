from tools import web


class FakeResponse:
    def __init__(self, text="", status_code=200, content_type="text/html"):
        self.text = text
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}


def test_fetch_url_rejects_non_http_scheme():
    result = web.fetch_url("file:///etc/passwd")
    assert "unsupported URL scheme" in result


def test_fetch_url_strips_html_tags(monkeypatch):
    html = "<html><head><style>.x{}</style></head><body><h1>Title</h1><p>Hello world</p></body></html>"
    monkeypatch.setattr(web.requests, "get", lambda *a, **k: FakeResponse(text=html))
    result = web.fetch_url("https://example.com")
    assert "Title" in result
    assert "Hello world" in result
    assert ".x{}" not in result


def test_fetch_url_content_type_check_is_case_insensitive(monkeypatch):
    # Regression: a live run against weathersa.co.za returned a
    # `Content-Type: text/HTML` header (capital HTML). The original check
    # (`"html" in content_type`) missed it, fell through to the plain-text
    # branch, and leaked raw markup/JS into the model's context instead of
    # extracting text -- or reporting that the page had none.
    html = "<html><body><script>noise()</script><div id='root'></div></body></html>"
    monkeypatch.setattr(
        web.requests, "get", lambda *a, **k: FakeResponse(text=html, content_type="text/HTML")
    )
    result = web.fetch_url("https://example.com")
    assert "<html>" not in result
    assert "noise()" not in result


def test_fetch_url_reports_no_text_for_js_rendered_shell(monkeypatch):
    # A Cloudflare/SPA shell with no server-rendered text -- fetch_url can't
    # execute JS, so this should read as "nothing here," not a wall of markup.
    html = (
        "<html><head><script>var x=1;</script></head>"
        "<body><a href='#' aria-hidden='true' style='display:none'></a>"
        "<div id='root'></div></body></html>"
    )
    monkeypatch.setattr(
        web.requests, "get", lambda *a, **k: FakeResponse(text=html, content_type="text/HTML")
    )
    result = web.fetch_url("https://example.com")
    assert "No readable text content" in result


def test_fetch_url_skips_script_content(monkeypatch):
    html = "<html><body><script>var x = 'should not appear';</script><p>Visible</p></body></html>"
    monkeypatch.setattr(web.requests, "get", lambda *a, **k: FakeResponse(text=html))
    result = web.fetch_url("https://example.com")
    assert "Visible" in result
    assert "should not appear" not in result


def test_fetch_url_passes_through_plain_text(monkeypatch):
    monkeypatch.setattr(
        web.requests, "get", lambda *a, **k: FakeResponse(text="plain body", content_type="text/plain")
    )
    result = web.fetch_url("https://example.com/file.txt")
    assert "plain body" in result


def test_fetch_url_rejects_unsupported_content_type(monkeypatch):
    monkeypatch.setattr(
        web.requests, "get", lambda *a, **k: FakeResponse(text="binary", content_type="image/png")
    )
    result = web.fetch_url("https://example.com/image.png")
    assert "unsupported content type" in result


def test_fetch_url_reports_http_error_status(monkeypatch):
    monkeypatch.setattr(web.requests, "get", lambda *a, **k: FakeResponse(status_code=404))
    result = web.fetch_url("https://example.com/missing")
    assert "HTTP 404" in result


def test_fetch_url_reports_request_exception(monkeypatch):
    def raiser(*a, **k):
        raise web.requests.RequestException("timed out")

    monkeypatch.setattr(web.requests, "get", raiser)
    result = web.fetch_url("https://example.com")
    assert "Error fetching URL" in result
    assert "timed out" in result


def test_fetch_url_truncates_long_content(monkeypatch):
    html = "<p>" + ("word " * 2000) + "</p>"
    monkeypatch.setattr(web.requests, "get", lambda *a, **k: FakeResponse(text=html))
    result = web.fetch_url("https://example.com", max_chars=50)
    assert "truncated to 50 characters" in result
