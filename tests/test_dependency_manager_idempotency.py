import os


def test_dependency_markers_make_ensure_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    from src.core import dependency_manager as dm

    dm._ENSURED_IN_PROCESS.clear()

    key = "test_dep:example"
    marker_path = dm._dependency_marker_path(key)
    if os.path.exists(marker_path):
        os.remove(marker_path)

    calls = {"ensure": 0}

    def ensure():
        calls["ensure"] += 1

    spec = dm.DependencySpec(
        key=key,
        description="Test dependency",
        check=lambda key=key: dm.is_dependency_marked_installed(key),
        ensure=ensure,
    )

    result1 = dm.ensure_all_required([spec])
    assert result1.ok
    assert calls["ensure"] == 1

    dm._ENSURED_IN_PROCESS.clear()
    result2 = dm.ensure_all_required([spec])
    assert result2.ok
    assert calls["ensure"] == 1
