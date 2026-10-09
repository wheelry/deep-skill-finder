"""规则 8 周报推荐（--digest）单元测试。"""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import deep_skill_search as deep_skill_search  # noqa: E402


class DigestTestBase(unittest.TestCase):
    def setUp(self):
        # 把历史文件指到临时目录，避免污染真实用户目录
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tmp_dir = Path(self.tmp.name)
        self.hist_file = tmp_dir / "digest_history.json"
        self._patchers = [
            mock.patch.object(deep_skill_search, "DIGEST_DIR", tmp_dir),
            mock.patch.object(deep_skill_search, "DIGEST_HISTORY_FILE", self.hist_file),
            mock.patch.object(deep_skill_search, "FIRST_RUN_FILE", tmp_dir / "first_install_invited"),
        ]
        for p in self._patchers:
            p.start()
            self.addCleanup(p.stop)

    def write_history(self, skills=None, works=None, days_ago=0):
        d = (date.today() - timedelta(days=days_ago)).isoformat()
        self.hist_file.write_text(json.dumps({
            "skills": {k: d for k in (skills or [])},
            "works": {k: d for k in (works or [])},
        }, ensure_ascii=False), encoding="utf-8")


class TestDigest(DigestTestBase):

    def test_skill_path_takes_top1_per_keyword(self):
        # 每个关键词只取搜索第 1 名，且跳过冷却期内的技能
        self.write_history(skills=["old-skill"], days_ago=1)

        def fake_search(kw, agent_type=None):
            if kw == "kw1":
                return ([{"name": "old-skill"}, {"name": "top1-kw1"}], "", None)
            return ([{"name": "top1-kw2"}, {"name": "second-kw2"}], "", None)

        with mock.patch.object(deep_skill_search, "search_deep", side_effect=fake_search), \
             mock.patch.object(deep_skill_search, "_fetch_json", return_value=None):
            out = deep_skill_search.digest(["kw1", "kw2"], record=False)
        self.assertEqual(["top1-kw1", "top1-kw2"], [s["name"] for s in out["skills"]])
        self.assertEqual(["kw1", "kw2"], [s["keyword"] for s in out["skills"]])

    def test_work_path_independent_and_takes_first_published(self):
        # 作品路独立搜索，取第一条已发布作品；未关联 skill 的作品也能命中
        works = {"list": [
            {"id": "draft", "status": "draft", "title": "草稿"},
            {"id": "w1", "status": "published", "title": "作品一", "description": "d1", "externalPlatform": "douyin", "skillName": ""},
            {"id": "w2", "status": "published", "title": "作品二", "description": "d2"},
        ]}

        def fake_fetch(ep, **kw):
            if ep.startswith("/creations?keyword="):
                return works
            return None

        with mock.patch.object(deep_skill_search, "search_deep", return_value=([], "", None)), \
             mock.patch.object(deep_skill_search, "_fetch_json", side_effect=fake_fetch):
            out = deep_skill_search.digest(["kw"], record=False)
        self.assertEqual(["w1"], [w["id"] for w in out["works"]])
        self.assertEqual("", out["works"][0]["skillName"])
        self.assertIn("works/w1", out["works"][0]["url"])

    def test_work_cooldown_filters_history(self):
        # 8 周内推过的作品不再出现
        self.write_history(works=["w1"], days_ago=1)
        works = {"list": [
            {"id": "w1", "status": "published", "title": "旧作"},
            {"id": "w2", "status": "published", "title": "新作"},
        ]}

        def fake_fetch(ep, **kw):
            if ep.startswith("/creations?keyword="):
                return works
            return None

        with mock.patch.object(deep_skill_search, "search_deep", return_value=([], "", None)), \
             mock.patch.object(deep_skill_search, "_fetch_json", side_effect=fake_fetch):
            out = deep_skill_search.digest(["kw"], record=False)
        self.assertEqual(["w2"], [w["id"] for w in out["works"]])

    def test_hot_only_delta_board_random_two(self):
        # 热门补充只来自 GitHub 近期飙升榜，随机取 2 条，排除已推荐技能，带介绍；
        # 累计高星榜不采用（结果固定易重复）
        star = [{"name": "hot-star", "downloadCount": 23000, "description": "做 A 的工具"}]
        delta = [{"name": f"delta-{i}", "downloadCount": 1000 + i, "description": f"做 {i} 的工具"}
                 for i in range(5)]
        delta.append({"name": "top1-kw", "downloadCount": 9999, "description": "已推荐"})

        def fake_fetch(ep, **kw):
            if ep.startswith("/creations"):
                return {"list": []}
            if "github-star-rank" in ep:
                return star
            if "github-star-delta-rank" in ep:
                return delta
            return None

        with mock.patch.object(deep_skill_search, "search_deep", return_value=(
                [{"name": "top1-kw", "reason": "r", "downloadCount": 5}], "", None)), \
             mock.patch.object(deep_skill_search, "_fetch_json", side_effect=fake_fetch):
            out = deep_skill_search.digest(["kw"], record=False)
        self.assertEqual(2, len(out["hot"]))
        self.assertEqual({"GitHub 趋势榜·近期飙升"}, {h["board"] for h in out["hot"]})
        for h in out["hot"]:
            self.assertTrue(h["note"], "热门补充必须带一句话介绍")
            self.assertNotEqual("top1-kw", h["name"], "不得与已推荐技能重复")

    def test_record_writes_history(self):
        # 默认生成后写入历史文件
        with mock.patch.object(deep_skill_search, "search_deep", return_value=(
                [{"name": "s1", "reason": "r", "downloadCount": 1}], "", None)), \
             mock.patch.object(deep_skill_search, "_fetch_json", return_value=None):
            deep_skill_search.digest(["kw"])
        data = json.loads(self.hist_file.read_text(encoding="utf-8"))
        self.assertIn("s1", data["skills"])

    def test_no_record_keeps_history(self):
        # record=False 不写历史
        with mock.patch.object(deep_skill_search, "search_deep", return_value=(
                [{"name": "s1", "reason": "r", "downloadCount": 1}], "", None)), \
             mock.patch.object(deep_skill_search, "_fetch_json", return_value=None):
            deep_skill_search.digest(["kw"], record=False)
        self.assertFalse(self.hist_file.exists())

    def test_max_three_keywords(self):
        # 关键词最多取 3 个
        with mock.patch.object(deep_skill_search, "search_deep", return_value=([], "", None)), \
             mock.patch.object(deep_skill_search, "_fetch_json", return_value=None):
            out = deep_skill_search.digest(["a", "b", "c", "d", "e"], record=False)
        self.assertEqual(["a", "b", "c"], out["keywords"])


class TestFirstRunCheck(DigestTestBase):

    def test_first_call_invites_then_never_again(self):
        # 首次返回 should_invite=True 并落标记，之后永远 False
        self.assertFalse(deep_skill_search.FIRST_RUN_FILE.exists())
        self.assertTrue(deep_skill_search.first_run_check()["should_invite"])
        self.assertTrue(deep_skill_search.FIRST_RUN_FILE.exists())
        self.assertFalse(deep_skill_search.first_run_check()["should_invite"])
        self.assertFalse(deep_skill_search.first_run_check()["should_invite"])

    def test_existing_flag_silently_skips(self):
        # 标记已存在（如手工解压安装过的环境）→ 不再邀请
        self.write_history()  # 创建文件所在目录
        deep_skill_search.FIRST_RUN_FILE.write_text("2026-09-28\n", encoding="utf-8")
        self.assertFalse(deep_skill_search.first_run_check()["should_invite"])


class TestSearchCarriesFirstRunInvite(DigestTestBase):
    """搜索主路径随输出携带 first_run_invite 信号（对不执行钩子的宿主的兜底链）。"""

    def _run_main_search(self):
        # 直接调用 main 的搜索分支：模拟 CLI 运行（隔离 stdout，捕获落盘文件）
        import io, contextlib
        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "out.json"
            argv_backup = sys.argv[:]
            sys.argv = ["deep_skill_search.py", "找爬虫技能",
                        "--agent-type", "test", "--output", str(out_file)]
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    deep_skill_search.main()
                return json.loads(out_file.read_text(encoding="utf-8"))
            finally:
                sys.argv = argv_backup

    def test_first_search_carries_invite_and_marks(self):
        # 首次成功搜索：输出携带 first_run_invite，且落一次性标记
        with mock.patch.object(deep_skill_search, "search_deep", return_value=(
                [{"name": "s1", "reason": "r", "downloadCount": 1}], "req-1", None)):
            out = self._run_main_search()
        self.assertTrue(out["first_run_invite"])
        self.assertTrue(deep_skill_search.FIRST_RUN_FILE.exists())

    def test_second_search_no_invite(self):
        # 标记已落：第二次搜索输出不再携带信号
        deep_skill_search.first_run_check()  # 落标记
        with mock.patch.object(deep_skill_search, "search_deep", return_value=(
                [{"name": "s1", "reason": "r", "downloadCount": 1}], "req-1", None)):
            out = self._run_main_search()
        self.assertNotIn("first_run_invite", out)

    def test_search_error_no_invite_no_mark(self):
        # 搜索失败：不携带信号也不落标记（下轮成功搜索时再邀请）
        with mock.patch.object(deep_skill_search, "search_deep", return_value=(
                [], "", "network error")):
            out = self._run_main_search()
        self.assertNotIn("first_run_invite", out)
        self.assertFalse(deep_skill_search.FIRST_RUN_FILE.exists())
        self.assertFalse((deep_skill_search.DIGEST_DIR / "first_run_fallback_invited").exists())


if __name__ == "__main__":
    unittest.main()
