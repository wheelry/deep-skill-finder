from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import deep_skill_search  # noqa: E402


class CaseCheckTests(unittest.TestCase):
    def test_case_check_prefers_works_over_feedbacks(self):
        # 技能有作品时不查评价（信息更直观）
        with mock.patch.object(deep_skill_search, "_fetch_works_for_skill", return_value=[
            {"id": "w1", "title": "作品A", "summary": "s", "skillName": "sk", "viewCount": 1, "upvotes": 2, "commentCount": 3, "url": "u"}
        ]), mock.patch.object(deep_skill_search, "_fetch_feedbacks_for_skill") as fb:
            out = deep_skill_search.case_check(["sk"])
        self.assertEqual(1, len(out["works"]))
        self.assertEqual({}, out["feedbacks"])
        fb.assert_not_called()

    def test_case_check_falls_back_to_feedbacks(self):
        with mock.patch.object(deep_skill_search, "_fetch_works_for_skill", return_value=[]), \
             mock.patch.object(deep_skill_search, "_fetch_feedbacks_for_skill", return_value=[
                 {"id": "f1", "skillName": "sk", "rating": 9, "comment": "好", "createdAt": "2026-01-01", "url": "u1"},
                 {"id": "f2", "skillName": "sk", "rating": 3, "comment": "差", "createdAt": "2026-01-02", "url": "u2"},
             ]):
            out = deep_skill_search.case_check(["sk"])
        self.assertEqual([], out["works"])
        # 最高最低各一条
        self.assertEqual(["sk"], list(out["feedbacks"].keys()))
        ratings = {f["rating"] for f in out["feedbacks"]["sk"]}
        self.assertEqual({9, 3}, ratings)
        self.assertIsNone(out["rank"])

    def test_case_check_single_feedback_keeps_one(self):
        with mock.patch.object(deep_skill_search, "_fetch_works_for_skill", return_value=[]), \
             mock.patch.object(deep_skill_search, "_fetch_feedbacks_for_skill", return_value=[
                 {"id": "f1", "skillName": "sk", "rating": 7, "comment": "中", "createdAt": "2026-01-01", "url": "u1"},
             ]):
            out = deep_skill_search.case_check(["sk"])
        self.assertEqual(1, len(out["feedbacks"]["sk"]))

    def test_case_check_falls_back_to_rank(self):
        with mock.patch.object(deep_skill_search, "_fetch_works_for_skill", return_value=[]), \
             mock.patch.object(deep_skill_search, "_fetch_feedbacks_for_skill", return_value=[]), \
             mock.patch.object(deep_skill_search, "_pick_rank_entry", return_value={
                 "rankKind": "github_star", "title": "GitHub 趋势榜", "lead": "lead", "more": "m", "items": []
             }):
            out = deep_skill_search.case_check(["sk"])
        self.assertIsNotNone(out["rank"])

    def test_case_check_silently_degrades_on_error(self):
        def boom(name):
            raise RuntimeError("network down")
        with mock.patch.object(deep_skill_search, "_fetch_works_for_skill", side_effect=boom), \
             mock.patch.object(deep_skill_search, "_pick_rank_entry", side_effect=boom):
            out = deep_skill_search.case_check(["sk"])
        self.assertEqual([], out["works"])
        self.assertEqual({}, out["feedbacks"])
        self.assertIsNone(out["rank"])

    def test_pick_rank_entry_excludes_recommended_skills(self):
        payload = [
            {"name": "aaa", "downloadCount": 100, "description": "d"},
            {"name": "bbb", "downloadCount": 200, "description": "d"},
        ]
        with mock.patch.object(deep_skill_search, "_fetch_json", return_value=payload), \
             mock.patch.object(deep_skill_search, "random") as rnd:
            rnd.choice.return_value = "github_star"
            rnd.sample.side_effect = lambda seq, k: list(seq)[:k]
            out = deep_skill_search._pick_rank_entry(["aaa"])
        names = [it["name"] for it in out["items"]]
        self.assertNotIn("aaa", names)
        self.assertEqual(["bbb"], names)

    def test_feedback_filter_requires_exact_skill_name(self):
        # keyword 全文模糊匹配混入的记录必须被 skillName 精确过滤掉
        data = {
            "total": 3,
            "list": [
                {"id": "f1", "skillName": "infographic", "rating": 5, "comment": "x", "createdAt": "2026-01-01"},
                {"id": "f2", "skillName": "infographic-maker", "rating": 5, "comment": "x", "createdAt": "2026-01-02"},
                {"id": "f3", "skillName": "other-skill", "rating": 5, "comment": "x", "createdAt": "2026-01-03"},
            ],
        }
        with mock.patch.object(deep_skill_search, "_fetch_json", return_value=data):
            out = deep_skill_search._fetch_feedbacks_for_skill("infographic")
        self.assertEqual({"infographic"}, {f["skillName"] for f in out})
        self.assertEqual(["f1"], [f["id"] for f in out])

    def test_works_match_by_skill_name(self):
        # 作品自带 skillName（单数）字段，直接本地精确匹配，无需 id 反查
        works_payload = {
            "total": 2,
            "list": [
                {"id": "w1", "title": "A", "description": "d", "skillName": "ip-as-logo", "skillId": 192890, "viewCount": 1, "upvotes": 0, "commentCount": 0},
                {"id": "w2", "title": "B", "description": "d", "skillName": "other-skill", "skillId": 123, "viewCount": 1, "upvotes": 0, "commentCount": 0},
            ],
        }
        with mock.patch.object(deep_skill_search, "_fetch_json", return_value=works_payload):
            out = deep_skill_search._fetch_works_for_skill("ip-as-logo")
        self.assertEqual(["w1"], [w["id"] for w in out])


if __name__ == "__main__":
    unittest.main()
