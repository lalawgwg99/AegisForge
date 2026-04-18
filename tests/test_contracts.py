from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

ROOT = Path("/tmp/aegisforge-contract-tests")


@pytest.fixture(autouse=True)
def clean_root():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["AEGISFORGE_ROOT"] = str(ROOT)
    yield
    os.environ.pop("AEGISFORGE_ROOT", None)
    if ROOT.exists():
        shutil.rmtree(ROOT)


class TestSDKContract:
    def test_safety_result_contract(self):
        from aegisforge import AegisForge

        result = AegisForge(ROOT).safety_check("read config", "cat config.yaml", profile="balanced")
        payload = result.to_dict()

        assert set(payload.keys()) == {
            "decision",
            "reason",
            "profile",
            "risk_score",
            "evidence",
            "decision_id",
        }
        assert payload["decision"] in {"allow", "ask", "block"}
        assert isinstance(payload["evidence"], list)

    def test_preflight_result_contract(self):
        from aegisforge import AegisForge

        af = AegisForge(ROOT)
        af.capture("tool", "timeout", "timeout after 30s")
        af.causal_distill(max_lanes=4, min_support=1)
        preflight = af.preflight("run sync", "api timeout", top_k=3).to_dict()

        assert set(preflight.keys()) == {"action", "guardrails", "brief"}
        assert isinstance(preflight["guardrails"], list)
        assert isinstance(preflight["brief"], str)

    def test_recovery_plan_contract(self):
        from aegisforge import AegisForge

        plan = AegisForge(ROOT).recover("timeout", ["retry", "restart"], explore_rate=0.0).to_dict()
        assert set(plan.keys()) == {"failure_class", "chosen_strategy", "mode", "ranked"}
        assert plan["mode"] in {"exploit", "explore"}
        assert isinstance(plan["ranked"], list)


class TestMCPContract:
    def test_mcp_tool_return_shapes(self):
        pytest.importorskip("mcp")
        from aegisforge import mcp_server

        safety = mcp_server.aegis_safety_check(action="read config", content="cat config", profile="balanced")
        assert {"decision", "reason", "profile", "risk_score", "evidence", "decision_id"} <= set(safety.keys())

        capture = mcp_server.aegis_capture(source="tool", error_type="timeout", message="request timeout 30s")
        assert {"id", "timestamp", "source", "error_type", "message"} <= set(capture.keys())

        preflight = mcp_server.aegis_preflight(action="run sync", content="api timeout", top_k=3)
        assert {"action", "content", "injected_guardrails", "preflight_brief"} <= set(preflight.keys())

        llm_stats = mcp_server.aegis_llm_stats()
        assert {"totals", "error_classifications", "fallback_reasons"} <= set(llm_stats.keys())
