import pytest
from app.tts import get_provider
from app.tts.fake import FakeProvider


def test_get_builtin_provider():
    p = get_provider("fake", options={})
    assert isinstance(p, FakeProvider)
    assert p.name == "fake"


def test_get_provider_passes_options():
    p = get_provider("fake", options={"sample_rate": 16000})
    assert p.sample_rate == 16000


def test_unknown_name_raises():
    with pytest.raises(KeyError, match="Unknown TTS provider"):
        get_provider("nope", options={})


def test_dotted_module_path_loads_external_provider(tmp_path, monkeypatch):
    # Build a tiny external provider in a temp module
    import sys, types
    mod = types.ModuleType("my_tts_pkg")
    class MyProvider:
        name = "mine"
        def __init__(self, **opts): self.opts = opts
        def synthesize(self, text, voice_id): raise NotImplementedError
        def voice_for_role(self, role): return "v"
    mod.MyProvider = MyProvider
    sys.modules["my_tts_pkg"] = mod
    p = get_provider("my_tts_pkg.MyProvider", options={"foo": 1})
    assert p.__class__.__name__ == "MyProvider"
    assert p.opts == {"foo": 1}
