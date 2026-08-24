import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import skill_feedback  # noqa: E402


class SkillFeedbackTests(unittest.TestCase):
    def test_codex_roots_do_not_guess_other_agent_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = Path(temp_dir) / "codex-home"
            other_home = Path(temp_dir) / "other-agent-home"
            environment = {
                "CODEX_HOME": str(codex_home),
                "OTHER_AGENT_USER_DATA_DIR": str(other_home),
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                roots = skill_feedback._codex_trajectory_roots()

            self.assertIn(codex_home / "sessions", roots)
            self.assertIn(codex_home / "archived_sessions", roots)
            self.assertFalse(any(str(other_home) in str(root) for root in roots))

    def test_codex_provider_discovers_strong_skill_signals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            records = [
                {
                    "timestamp": timestamp,
                    "type": "response_item",
                    "payload": {
                        "type": "custom_tool_call",
                        "input": {
                            "cmd": "sed -n '1,200p' /tmp/.codex/skills/demo-skill/SKILL.md"
                        },
                    },
                },
                {
                    "timestamp": timestamp,
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "请使用 $another-skill 完成任务",
                    },
                },
            ]
            trajectory = root / "rollout-550e8400-e29b-41d4-a716-446655440000.jsonl"
            trajectory.write_text(
                "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
                encoding="utf-8",
            )

            result = skill_feedback.discover_skills([root], days=30)

            self.assertEqual(skill_feedback.CODEX_PROVIDER_ID, result["provider"])
            self.assertFalse(result["needsAgentDiscovery"])
            self.assertEqual({"demo-skill", "another-skill"}, {item["name"] for item in result["skills"]})

    def test_unknown_agent_fallback_requires_current_agent_discovery(self):
        result = skill_feedback._agent_discovery_result()

        self.assertTrue(result["needsAgentDiscovery"])
        self.assertIsNone(result["provider"])
        self.assertIn("current Agent", result["message"])
        self.assertTrue(any("unknown vendor format" in item for item in result["invariants"]))

    def test_codex_provider_does_not_apply_to_another_agent(self):
        with mock.patch.object(
            skill_feedback,
            "_codex_trajectory_roots",
            return_value=[Path("/tmp/fake-codex-sessions")],
        ), mock.patch.object(Path, "is_dir", return_value=True), mock.patch.object(
            Path,
            "rglob",
            return_value=iter([Path("/tmp/fake-codex-sessions/rollout.jsonl")]),
        ):
            provider = skill_feedback.probe_providers("NovelAgent")[0]

        self.assertTrue(provider["detected"])
        self.assertFalse(provider["applicable"])

    def test_redaction_and_validation_accept_normalized_draft(self):
        draft = {
            "schemaVersion": "1.3",
            "skill": {"name": "demo-skill"},
            "evaluation": {
                "usageScenario": "read /Users/alice/private.txt",
                "skillPerformance": "used a domain workflow and completed the task",
                "rating": 8,
                "comment": "contact me@example.com with Authorization: Bearer abcdef123456",
            },
        }

        sanitized = skill_feedback.sanitize_value(draft)

        self.assertEqual([], skill_feedback.validate_payload(sanitized))
        self.assertIn("[REDACTED_EMAIL]", sanitized["evaluation"]["comment"])
        self.assertIn("[REDACTED_SECRET]", sanitized["evaluation"]["comment"])
        self.assertIn("[REDACTED_HOME]", sanitized["evaluation"]["usageScenario"])

    def test_validation_requires_exact_four_evaluation_fields(self):
        draft = {
            "schemaVersion": "1.3",
            "skill": {"name": "demo-skill"},
            "evaluation": {
                "usageScenario": "demo task",
                "skillPerformance": "provided a workflow and contributed to the result",
                "rating": 8,
                "comment": "useful",
                "strengths": ["legacy field"],
            },
        }

        errors = skill_feedback.validate_payload(draft)

        self.assertTrue(
            any(
                "only accepts usageScenario, skillPerformance, rating, and comment" in error
                for error in errors
            )
        )

        del draft["evaluation"]["strengths"]
        del draft["evaluation"]["skillPerformance"]
        errors = skill_feedback.validate_payload(draft)

        self.assertIn("evaluation.skillPerformance is required", errors)

        draft["evaluation"]["skillPerformance"] = "provided a workflow"
        del draft["evaluation"]["rating"]
        del draft["evaluation"]["comment"]
        errors = skill_feedback.validate_payload(draft)

        self.assertIn("evaluation.rating must be between 1 and 10", errors)
        self.assertIn("evaluation.comment field is required; use null when omitted", errors)

    def test_validation_accepts_ten_point_rating_and_optional_comment(self):
        draft = {
            "schemaVersion": "1.3",
            "skill": {"name": "demo-skill"},
            "evaluation": {
                "usageScenario": "demo task",
                "skillPerformance": "provided a workflow",
                "rating": 10,
                "comment": None,
            },
        }

        self.assertEqual([], skill_feedback.validate_payload(draft))

        draft["evaluation"]["rating"] = 10.1
        self.assertIn(
            "evaluation.rating must be between 1 and 10",
            skill_feedback.validate_payload(draft),
        )

    def test_submit_refuses_without_review_assertion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            draft_path = Path(temp_dir) / "draft.json"
            outbox_path = Path(temp_dir) / "outbox.jsonl"
            draft_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": "1.3",
                        "skill": {"name": "demo-skill"},
                        "evaluation": {
                            "usageScenario": "demo task",
                            "skillPerformance": "provided a workflow",
                            "rating": 8,
                            "comment": None,
                        },
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                confirmed=False,
                input=str(draft_path),
                outbox=str(outbox_path),
            )

            with contextlib.redirect_stderr(io.StringIO()):
                exit_code = skill_feedback._command_submit(args)

            self.assertEqual(2, exit_code)
            self.assertFalse(outbox_path.exists())

    def test_submit_accepts_reviewed_usage_scenario(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            draft_path = Path(temp_dir) / "draft.json"
            outbox_path = Path(temp_dir) / "outbox.jsonl"
            draft_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": "1.3",
                        "skill": {"name": "demo-skill"},
                        "evaluation": {
                            "usageScenario": "demo task",
                            "skillPerformance": "provided a workflow",
                            "rating": 8,
                            "comment": "useful",
                        },
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                confirmed=True,
                input=str(draft_path),
                outbox=str(outbox_path),
            )

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = skill_feedback._command_submit(args)

            self.assertEqual(0, exit_code)
            record = json.loads(outbox_path.read_text(encoding="utf-8"))
            self.assertEqual("demo task", record["payload"]["evaluation"]["usageScenario"])


if __name__ == "__main__":
    unittest.main()
