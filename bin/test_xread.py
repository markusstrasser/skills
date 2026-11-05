"""xread must name a post from any URL form and keep unavailable apart from transport failure."""

import importlib.machinery
import importlib.util
from pathlib import Path
import urllib.error

import pytest

loader = importlib.machinery.SourceFileLoader("xread", str(Path(__file__).with_name("xread")))
spec = importlib.util.spec_from_loader("xread", loader)
xread = importlib.util.module_from_spec(spec)
loader.exec_module(xread)


def post(identifier, text, **extra):
    return {
        "id": identifier,
        "url": f"https://x.com/a/status/{identifier}",
        "text": text,
        "author": {"screen_name": "a", "name": "A"},
        **extra,
    }


@pytest.mark.parametrize(
    "target",
    [
        "123",
        "https://x.com/a/status/123",
        "https://twitter.com/a/status/123?s=20",
        "https://x.com/i/web/status/123/photo/1",
        "https://fxtwitter.com/a/statuses/123",
    ],
)
def test_post_id_accepts_url_forms(target):
    assert xread.post_id(target) == "123"


def test_post_id_rejects_profile_url():
    with pytest.raises(ValueError):
        xread.post_id("https://x.com/a")


def test_render_keeps_media_quote_and_note():
    status = post(
        "1",
        "hello",
        media={"all": [{"type": "photo", "url": "https://pbs.twimg.com/x.jpg"}]},
        community_note={"text": "context"},
        quote=post("2", "quoted line"),
    )
    output = xread.render({"status": status, "thread": [status]})
    assert "[photo] https://pbs.twimg.com/x.jpg" in output
    assert "Community note: context" in output
    assert "> quoted line" in output
    assert "Thread of" not in output


def test_render_marks_requested_post_in_thread():
    first, second = post("1", "one"), post("2", "two")
    output = xread.render({"status": second, "thread": [first, second]})
    assert "Thread of 2 posts" in output
    assert "--- 2/2 (requested)" in output


def test_missing_status_is_unavailable():
    with pytest.raises(xread.Unavailable):
        xread.render({"code": 404})


def raiser(exc):
    def urlopen(*_args, **_kwargs):
        raise exc

    return urlopen


def test_exit_codes_separate_gone_from_transport(monkeypatch, capsys):
    monkeypatch.setattr(xread.time, "sleep", lambda _seconds: None)
    gone = urllib.error.HTTPError("u", 404, "gone", {}, None)
    monkeypatch.setattr(xread.urllib.request, "urlopen", raiser(gone))
    assert xread.main(["1"]) == 1
    assert "ask for pasted text" in capsys.readouterr().err

    monkeypatch.setattr(xread.urllib.request, "urlopen", raiser(urllib.error.URLError("dns")))
    assert xread.main(["1"]) == 2
    assert "says nothing about the post" in capsys.readouterr().err
