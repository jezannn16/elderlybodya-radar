import pytest
from radar.config import load_config, require_env


def test_load_config_merges_and_lowercases_keywords(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(
        "timezone: Europe/Moscow\n"
        "run_hour: 6\n"
        "drafts_per_day: 5\n"
        "language: ru\n"
        "keywords:\n"
        "  ru: [Жим]\n"
        "  en: [Bench]\n"
        "sources:\n"
        "  reddit:\n"
        "    enabled: true\n"
        "    subreddits: [powerlifting]\n",
        encoding="utf-8",
    )
    cfg = load_config(str(p))
    assert cfg.drafts_per_day == 5
    assert cfg.keywords == ["жим", "bench"]
    assert cfg.sources["reddit"]["subreddits"] == ["powerlifting"]


def test_require_env_raises_when_missing(monkeypatch):
    monkeypatch.delenv("NOPE", raising=False)
    with pytest.raises(RuntimeError):
        require_env("NOPE")
