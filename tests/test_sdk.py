from __future__ import annotations

import shutil
from pathlib import Path

import pytest

ROOT = Path("/tmp/aegisforge-sdk-tests")


@pytest.fixture(autouse=True)
def clean_root():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)
    yield
    if ROOT.exists():
        shutil.rmtree(ROOT)


class TestSDK:
    def test_safety_check_allow(self):
        from aegisforge import AegisForge
        af = AegisForge(ROOT)
        r = af.safety_check("read config", "cat config.yaml")
        assert r.allowed
        assert not r.blocked
        assert r.decision == "allow"

    def test_safety_check_block(self):
        from aegisforge import AegisForge
        af = AegisForge(ROOT)
        r = af.safety_check("share", "token=sk-12345678901234567890ab", profile="dev")
        assert r.blocked
        assert r.decision_id is not None

    def test_safety_check_ask(self):
        from aegisforge import AegisForge
        af = AegisForge(ROOT)
        r = af.safety_check("delete table", "DROP TABLE users")
        assert r.needs_approval

    def test_to_dict(self):
        from aegisforge import AegisForge
        af = AegisForge(ROOT)
        r = af.safety_check("read", "hello")
        d = r.to_dict()
        assert "decision" in d
        assert "evidence" in d

    def test_preflight(self):
        from aegisforge import AegisForge
        af = AegisForge(ROOT)
        for _ in range(3):
            af.capture("tool", "timeout", "request timeout 30s")
        af.distill()
        af.causal_distill()
        r = af.preflight("run sync", "api timeout")
        assert r.has_guardrails
        assert r.count >= 1
        assert r.brief

    def test_capture_distill_inject(self):
        from aegisforge import AegisForge
        af = AegisForge(ROOT)
        af.capture("tool", "timeout", "timeout 30s")
        af.capture("tool", "timeout", "upstream timeout")
        lessons = af.distill()
        assert len(lessons) >= 1
        picked = af.inject(top_k=2)
        assert len(picked) >= 1

    def test_recovery(self):
        from aegisforge import AegisForge
        af = AegisForge(ROOT)
        plan = af.recover("timeout", ["retry", "restart"], explore_rate=0.0)
        assert plan.chosen_strategy in {"retry", "restart"}
        assert plan.mode == "exploit"
        r = af.record_outcome("timeout", "retry", True)
        assert r["attempts"] == 1
        stats = af.recovery_stats("timeout")
        assert stats["total_attempts"] == 1

    def test_health_and_forget(self):
        from aegisforge import AegisForge
        af = AegisForge(ROOT)
        h = af.health()
        assert "errors" in h
        f = af.forget()
        assert "before" in f

    def test_benchmark(self):
        from aegisforge import AegisForge
        af = AegisForge(ROOT)
        r = af.benchmark(rounds=50, seed=42)
        assert r["adaptive_success_rate"] > 0


class TestLogImport:
    def test_import_jsonl(self, tmp_path):
        from aegisforge import AegisForge
        log_file = tmp_path / "agent.jsonl"
        log_file.write_text(
            '{"level":"error","message":"request timeout after 30s","source":"api"}\n'
            '{"level":"info","message":"all good","source":"api"}\n'
            '{"level":"error","message":"401 unauthorized","source":"auth"}\n'
        )
        af = AegisForge(ROOT)
        r = af.import_log(log_file)
        assert r["imported"] == 2
        assert r["skipped"] == 1

    def test_import_text(self, tmp_path):
        from aegisforge import AegisForge
        log_file = tmp_path / "agent.log"
        log_file.write_text(
            "2024-01-01 INFO: starting\n"
            "2024-01-01 ERROR: connection timeout to db\n"
            "2024-01-01 INFO: done\n"
        )
        af = AegisForge(ROOT)
        r = af.import_log(log_file)
        assert r["imported"] == 1

    def test_import_field_map(self, tmp_path):
        from aegisforge import AegisForge
        log_file = tmp_path / "custom.jsonl"
        log_file.write_text(
            '{"severity":"error","msg":"rate limit exceeded","component":"gateway"}\n'
        )
        af = AegisForge(ROOT)
        r = af.import_log(log_file, field_map={"message": "msg", "source": "component", "error_type": "severity"})
        assert r["imported"] == 1

    def test_import_not_found(self):
        from aegisforge import AegisForge
        af = AegisForge(ROOT)
        r = af.import_log("/nonexistent/file.log")
        assert r["imported"] == 0
        assert "error" in r


class TestLLMExtract:
    def test_fallback_to_template(self):
        """When LLM is unreachable, falls back to template extraction."""
        from aegisforge.llm_extract import distill_with_llm
        from aegisforge.core import capture_failure
        capture_failure(ROOT, "tool", "timeout", "request timeout 30s")
        capture_failure(ROOT, "tool", "timeout", "upstream timeout")
        lessons = distill_with_llm(ROOT, max_lessons=3, api_url="http://localhost:99999/v1")
        assert len(lessons) >= 1  # fell back to template

    def test_extract_json_array(self):
        from aegisforge.llm_extract import _extract_json_array
        assert _extract_json_array('["a","b"]') == ["a", "b"]
        assert _extract_json_array('```json\n["a"]\n```') == ["a"]
        assert _extract_json_array("not json") is None
