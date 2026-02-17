import core.lifecycle as lifecycle_mod
from core.settings_typed import SettingsStore


def _make_store(tmp_path):
    return SettingsStore(str(tmp_path / "settings.json"))


def test_set_agent_running_starts_and_enables(tmp_path, monkeypatch):
    store = _make_store(tmp_path)
    monkeypatch.setattr(lifecycle_mod, "get_settings_store", lambda: store)
    manager = lifecycle_mod.LifecycleManager(tmp_path)

    result = manager.set_agent_running("finance", True)
    assert result["success"] is True

    status = manager.get_status()
    assert status["agents"]["finance"]["running"] is True
    assert status["agents_enabled"]["finance"] is True


def test_set_agent_running_stops_without_disabling(tmp_path, monkeypatch):
    store = _make_store(tmp_path)
    monkeypatch.setattr(lifecycle_mod, "get_settings_store", lambda: store)
    manager = lifecycle_mod.LifecycleManager(tmp_path)

    manager.set_agent_running("finance", True)
    result = manager.set_agent_running("finance", False)
    assert result["success"] is True

    status = manager.get_status()
    assert status["agents"]["finance"]["running"] is False
    assert status["agents_enabled"]["finance"] is True


def test_set_agent_enabled_disables_and_stops(tmp_path, monkeypatch):
    store = _make_store(tmp_path)
    monkeypatch.setattr(lifecycle_mod, "get_settings_store", lambda: store)
    manager = lifecycle_mod.LifecycleManager(tmp_path)

    manager.set_agent_running("finance", True)
    result = manager.set_agent_enabled("finance", False)
    assert result["success"] is True

    status = manager.get_status()
    assert status["agents"]["finance"]["running"] is False
    assert status["agents_enabled"]["finance"] is False
