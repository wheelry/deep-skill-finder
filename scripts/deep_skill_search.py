#!/usr/bin/env python3
"""搜索 Meyo 社区 skill。

用法:
  deep_skill_search.py "帮我分析数据"                    # 语义深度搜索
"""

import argparse
import json
import os
import random
import socket
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, timedelta
from pathlib import Path

# Windows 控制台默认 cp936，中文/emoji 会 UnicodeEncodeError，统一切到 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def _read_json(path: Path) -> dict:
    try:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {}


CLIENT_ID_FILE = Path.home() / ".deep_skill_finder" / "client_id"


def get_client_id() -> str:
    """返回本机持久化的 clientId，不存在则生成并写入 ~/.deep_skill_finder/client_id。"""
    try:
        if CLIENT_ID_FILE.exists():
            cid = CLIENT_ID_FILE.read_text(encoding="utf-8").strip()
            if cid:
                return cid
        CLIENT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        cid = str(uuid.uuid4())
        CLIENT_ID_FILE.write_text(cid + "\n", encoding="utf-8")
        return cid
    except OSError:
        return ""


def get_api_url_candidates():
    """返回 API URL 候选列表（优先级从高到低）。"""
    candidates = []

    # 1. 环境变量 MEYO_API_URL（逗号分隔列表）
    env_urls = os.environ.get("MEYO_API_URL", "")
    for u in env_urls.split(","):
        u = u.strip().rstrip("/")
        if u:
            candidates.append(u)

    # 2. app.config.json 中的配置
    app_config = _read_json(Path.home() / ".meyo_agent" / "app.config.json")
    configured = app_config.get("settings", {}).get("meyoApiUrl", "")
    if configured:
        candidates.append(configured.rstrip("/"))

    # 3. 兜底
    if not candidates:
        candidates = ["https://www.deepskill.market/api/v1"]

    return candidates


def _probe_api_url(url: str, token: str) -> bool:
    """探测 API URL 是否可认证（GET /skills，不返回 401 即可）。"""
    headers = {"User-Agent": "deep-skill-finder/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(f"{url}/skills?limit=1", headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status < 400
    except urllib.error.HTTPError as e:
        return e.code != 401
    except Exception:
        return False


# 缓存探测结果
_resolved_api_url = None


def get_api_url():
    """返回第一个可认证的 API URL（带缓存）。"""
    global _resolved_api_url
    if _resolved_api_url:
        return _resolved_api_url

    candidates = get_api_url_candidates()
    token = get_api_token()

    for url in candidates:
        if _probe_api_url(url, token):
            _resolved_api_url = url
            return url

    # 全部失败，返回第一个候选（兜底）
    _resolved_api_url = candidates[0]
    return _resolved_api_url


def get_api_token():
    app_config = _read_json(Path.home() / ".meyo_agent" / "app.config.json")
    settings = app_config.get("settings", {})
    return settings.get("meyoApiKey") or settings.get("meyoToken") or os.environ.get("MEYO_API_KEY", "")


def api_request(endpoint: str, method: str = "GET", data: dict = None, extra_headers: dict = None, timeout: int = 15) -> dict:
    """发送 API 请求，返回 JSON 响应。"""
    api_url = get_api_url()
    url = f"{api_url}/{endpoint.lstrip('/')}"
    token = get_api_token()

    headers = {"User-Agent": "deep-skill-finder/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        for k, v in extra_headers.items():
            if v:
                headers[k] = v

    body = None
    if data:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            return result
    except urllib.error.HTTPError as e:
        return {"code": e.code, "error": True, "errorType": "http"}
    except urllib.error.URLError as e:
        error_type = "timeout" if isinstance(e.reason, (TimeoutError, socket.timeout)) else "network"
        return {"code": 0, "error": True, "errorType": error_type}
    except (TimeoutError, socket.timeout):
        return {"code": 0, "error": True, "errorType": "timeout"}
    except Exception:
        return {"code": 0, "error": True, "errorType": "service"}


def _structured_search_error(result: dict) -> dict:
    """Return a stable, user-safe error payload for an Agent to interpret."""
    error_type = result.get("errorType", "service")
    status = result.get("code", 0)
    if error_type == "timeout":
        code, message = "search_timeout", "搜索服务请求超时"
    elif error_type == "network":
        code, message = "search_network_error", "无法连接搜索服务"
    elif error_type == "http" and status >= 500:
        code, message = "search_service_error", "搜索服务暂时不可用"
    elif error_type == "http":
        code, message = "search_request_error", "搜索请求未被服务接受"
    else:
        code, message = "search_service_error", "搜索服务遇到内部错误"
    error = {"code": code, "message": message}
    if status:
        error["httpStatus"] = status
    return error


def _parse_skill_item(s: dict) -> dict:
    """提取 deep search 返回的 skill 字段（DeepSearchSkillItemVO: name/description/downloadCount/reason）。"""
    return {
        "name": s.get("name", ""),
        "description": s.get("description", ""),
        "downloadCount": s.get("downloadCount", 0),
        "reason": s.get("reason", ""),
    }


def get_skill_version() -> str:
    """从 SKILL.md frontmatter 读取当前版本号。"""
    skill_md = Path(__file__).resolve().parent.parent / "SKILL.md"
    if skill_md.exists():
        m = re.search(r'version:\s*"([^"]+)"', skill_md.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return "unknown"


def search_deep(content: str, agent_type: str = None) -> tuple:
    """语义深度搜索（如果 API 支持）。

    API 已按相关性排序，返回 Top5 候选。
    返回 (skills, request_id, error)，request_id 用于串联下载链路；成功时 error 为 None。
    """
    params = {"query": content, "ref": "meyo"}
    if agent_type:
        params["agentType"] = agent_type
    version = get_skill_version()
    if version != "unknown":
        params["skillVersion"] = version
    query_string = urllib.parse.urlencode(params)
    result = api_request(f"/skills/search/deep?{query_string}", extra_headers={"X-Client-Id": get_client_id()}, timeout=60)

    if result.get("error"):
        return [], "", _structured_search_error(result)

    data = result.get("data", [])
    # DeepSearchResultVO 在 data 顶层带 requestId
    request_id = ""
    if isinstance(data, dict):
        request_id = data.get("requestId", "") or ""
        skills_raw = data.get("items") or data.get("list") or []
        if isinstance(skills_raw, list) and skills_raw and isinstance(skills_raw[0], dict) and "skills" in skills_raw[0]:
            # 分组结构 [{scene, skills:[...]}]
            skills = []
            for group in skills_raw:
                for item in group.get("skills", []) or []:
                    if isinstance(item, dict):
                        skills.append(item)
        else:
            skills = skills_raw if isinstance(skills_raw, list) else []
    elif isinstance(data, list):
        skills = data
    else:
        skills = []
    if not isinstance(skills, list):
        return [], request_id, None

    parsed = [_parse_skill_item(s) for s in skills]
    return parsed, request_id, None

  
def _format_count(n) -> str:
    """数字缩写：263875 -> 263.9k，1930 -> 1.9k，未满千原样输出。"""
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        return str(n or 0)
    if n >= 10000:
        return f"{n / 10000:.1f}w"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


# ---------- 案例展示（三级降级：作品 → 评价 → 榜单） ----------

RANK_ENTRY_URL = "https://www.deepskill.market/skill/skill?name={name}&ref=deep-skill-finder"
WORK_URL = "https://www.deepskill.market/works/{id}"
FEEDBACK_URL = "https://www.deepskill.market/feedback/detail/{id}"

# 榜单注册表：随机选一个榜，条目渲染各配一段文案（key 与返回 JSON 中 rankKind 对应）
RANK_REGISTRY = {
    "github_star": {
        "title": "GitHub 趋势榜",
        "lead": "本次推荐之外，开源社区用 Star 投出来的高人气技能还有：",
        "metric": "star",
        "url": "/deepskill/skills/github-star-rank?limit=50",
    },
    "github_star_delta": {
        "title": "GitHub 趋势榜",
        "lead": "本次推荐之外，最近 30 天在 GitHub 上快速走红的技能还有：",
        "metric": "star",
        "url": "/deepskill/skills/github-star-delta-rank?limit=50",
    },
    "official_authors": {
        "title": "权威来源榜",
        "lead": "这些技能作者都经过平台认证，出品稳定可靠，可以去逛逛：",
        "metric": "skillCount",
        "url": "/deepskill/official-authors",
    },
    # Market 热搜榜上线后加入：
    # "market_hot": {
    #     "title": "站内热门榜",
    #     "lead": "本次推荐之外，站内用户最近搜得最多的技能还有：",
    #     "metric": "download",
    #     "url": "/deepskill/skills/stat-rank?tag=searchCount&limit=50",
    # },
}


def _fetch_json(endpoint: str, timeout: int = 15):
    """GET 请求，失败返回 None（案例展示是附加信息，失败静默降级）。"""
    result = api_request(endpoint, timeout=timeout)
    if isinstance(result, dict) and result.get("code") == 200:
        return result.get("data")
    return None


_works_cache = None


def _load_all_works() -> list:
    """全量拉取作品（约 200+ 条，两三页），供按 skillId 匹配。带模块级缓存。"""
    global _works_cache
    if _works_cache is not None:
        return _works_cache
    works = []
    for page in (1, 2, 3, 4, 5):
        data = _fetch_json(f"/creations?page={page}&pageSize=100&sort=sortOrder")
        if not isinstance(data, dict):
            break
        lst = data.get("list") or []
        works.extend(lst)
        total = data.get("total") or 0
        if not lst or len(works) >= total:
            break
    _works_cache = works
    return works


def _fetch_works_for_skill(skill_name: str) -> list:
    """按技能名查作品。

    作品列表自带 skillName 字段（有关联的作品 100% 携带），直接全量拉取后本地精确匹配，
    无额外请求；skillNames（复数）字段恒为空，注意区分。
    """
    works = []
    for it in _load_all_works():
        if not isinstance(it, dict) or it.get("skillName") != skill_name:
            continue
        works.append({
            "id": it.get("id", ""),
            "title": it.get("title", ""),
            "summary": (it.get("description") or "").strip(),
            "skillName": skill_name,
            "viewCount": it.get("viewCount", 0),
            "upvotes": it.get("upvotes", 0),
            "commentCount": it.get("commentCount", 0),
            "url": WORK_URL.format(id=it.get("id", "")),
        })
    # 按互动量降序（点赞 > 评论 > 浏览）
    works.sort(key=lambda w: (w["upvotes"], w["commentCount"], w["viewCount"]), reverse=True)
    return works


def _fetch_feedbacks_for_skill(skill_name: str) -> list:
    """按技能名查评价。keyword 是全文模糊匹配，必须客户端按 skillName 精确过滤。"""
    data = _fetch_json(f"/skill-feedback?keyword={urllib.parse.quote(skill_name)}&pageSize=100")
    if not isinstance(data, dict):
        return []
    feedbacks = []
    for it in data.get("list") or []:
        if isinstance(it, dict) and it.get("skillName") == skill_name:
            feedbacks.append({
                "id": it.get("id", ""),
                "skillName": it.get("skillName", ""),
                "rating": it.get("rating"),
                "comment": (it.get("comment") or "").strip(),
                "createdAt": it.get("createdAt", ""),
                "url": FEEDBACK_URL.format(id=it.get("id", "")),
            })
    # 最新在前
    feedbacks.sort(key=lambda f: f.get("createdAt", ""), reverse=True)
    return feedbacks


def _pick_rank_entry(skill_names: list) -> dict:
    """随机选一个榜 + 从中随机抽 3 个（剔除 Top5 已推荐技能），失败返回 None。"""
    kind = random.choice(list(RANK_REGISTRY.keys()))
    reg = RANK_REGISTRY[kind]
    data = _fetch_json(reg["url"])
    if not isinstance(data, list) or not data:
        return None
    entries = []
    for it in data:
        if not isinstance(it, dict):
            continue
        if it.get("name") in skill_names:
            continue  # 剔除已推荐
        if kind == "official_authors":
            entries.append({
                "name": it.get("author", ""),
                "metric": _format_count(it.get("skillCount", 0)) + " 个技能",
                "note": (it.get("description") or "").strip(),
                "url": f"https://www.deepskill.market/creator/{it.get('author', '')}",
            })
        else:
            entries.append({
                "name": it.get("name", ""),
                "metric": "⭐ " + _format_count(it.get("downloadCount", 0)),
                "note": (it.get("description") or "").strip(),
                "url": RANK_ENTRY_URL.format(name=urllib.parse.quote(it.get("name", ""))),
            })
    if not entries:
        return None
    picked = random.sample(entries, min(3, len(entries)))
    return {
        "rankKind": kind,
        "title": reg["title"],
        "lead": reg["lead"],
        "more": "https://www.deepskill.market/rank",
        "items": picked,
    }


def case_check(skill_names: list) -> dict:
    """对 Top5 技能做案例展示探测（三级降级，返回结构化 JSON 供 Agent 渲染）。

    逻辑：逐技能先查作品；无作品再查评价；所有技能都无作品时评价可用技能正常出评价区。
    有一条作品的技能就不用评价（信息更直观）；全部无作品、部分技能有评价时出评价区；
    全部无作品且无评价时随机榜单兜底。
    """
    skills = [n.strip() for n in skill_names if n and n.strip()][:5]
    works = []          # [{skillName, title, url, ...}]，按技能在 Top5 中的顺序收集
    feedback_by_skill = {}
    for name in skills:
        try:
            ws = _fetch_works_for_skill(name)
        except Exception:
            ws = []
        if ws:
            works.extend(ws)
            continue
        try:
            fb = _fetch_feedbacks_for_skill(name)
        except Exception:
            fb = []
        if fb:
            feedback_by_skill[name] = fb

    output = {"skills": skills, "works": [], "feedbacks": {}, "rank": None}

    if works:
        # 封顶 3 条，按互动量降序
        works.sort(key=lambda w: (w["upvotes"], w["commentCount"], w["viewCount"]), reverse=True)
        output["works"] = works[:3]

    # 有作品的技能本可跳过评价；但若没有任何作品，则展示有评价的技能的评价
    if not works and feedback_by_skill:
        # 每个技能取最高、最低各 1 条；并列/仅 1 条时只留 1 条
        fb_out = {}
        for name in skills:
            if name not in feedback_by_skill:
                continue
            lst = feedback_by_skill[name]
            rated = [f for f in lst if isinstance(f.get("rating"), (int, float))]
            if not rated:
                continue
            best = max(rated, key=lambda f: f["rating"])
            worst = min(rated, key=lambda f: f["rating"])
            if best["id"] == worst["id"]:
                fb_out[name] = [best]
            else:
                fb_out[name] = [best, worst]
        output["feedbacks"] = fb_out

    # 兜底：无作品且无可用评价 → 随机榜单
    if not output["works"] and not output["feedbacks"]:
        try:
            output["rank"] = _pick_rank_entry(skills)
        except Exception:
            output["rank"] = None

    return output


# ---- 每周技能推荐（cron digest，规则 8）----

DIGEST_DIR = Path.home() / ".deep_skill_finder"
DIGEST_HISTORY_FILE = DIGEST_DIR / "digest_history.json"
# 一次性邀请标记：放在 skill 目录内（重装/重新解压会清掉 → 重新邀请；
# git pull 升级不会清 → 不重复邀请）；skill 目录不可写时退回家目录
FIRST_RUN_FILE = Path(__file__).resolve().parent.parent / ".first_run_invited"
LEGACY_FIRST_RUN_FILE = DIGEST_DIR / "first_install_invited"
DIGEST_COOLDOWN_DAYS = 56
# 周报热门补充只用近期飙升榜：累计高星榜结果固定容易重复推同一批，不采用
DIGEST_BOARDS = ("github_star_delta",)
DIGEST_HOT_COUNT = 2  # 飙升榜每次随机取的条目数


def _load_digest_history() -> dict:
    """读取推送历史 {skills: {name: date}, works: {id: date}}，剔除超出冷却期的旧记录。"""
    data = _read_json(DIGEST_HISTORY_FILE)
    cutoff = (date.today() - timedelta(days=DIGEST_COOLDOWN_DAYS)).isoformat()
    out = {"skills": {}, "works": {}}
    for key in ("skills", "works"):
        for name, d in (data.get(key) or {}).items():
            if isinstance(d, str) and d >= cutoff:
                out[key][name] = d
    return out


def _record_digest_history(skill_names: list, work_ids: list):
    """把本次推送的技能/作品写入历史（保留文件里已有记录），失败静默。"""
    hist = _load_digest_history()
    today = date.today().isoformat()
    for name in skill_names:
        hist["skills"][name] = today
    for wid in work_ids:
        hist["works"][wid] = today
    try:
        DIGEST_DIR.mkdir(parents=True, exist_ok=True)
        # 每类最多保留最近 200 条，防止长期使用无限膨胀
        for key in ("skills", "works"):
            if len(hist[key]) > 200:
                keep = sorted(hist[key].items(), key=lambda kv: kv[1], reverse=True)[:200]
                hist[key] = dict(keep)
        DIGEST_HISTORY_FILE.write_text(
            json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def _compress_note(text: str, limit: int = 60) -> str:
    """取描述首行并截断，用作一句话介绍。"""
    return ((text or "").strip().splitlines() or [""])[0].strip()[:limit]


def first_run_check() -> dict:
    """首次加载自检：未发过周报邀请则返回 should_invite=True 并落标记文件（一次性）。

    标记存于 skill 目录内 .first_run_invited：重新安装/解压会重新触发邀请，
    git pull 升级不会；skill 目录不可写时退回家目录。旧版全局标记会被清理。
    除独立调用（Step 0.5/2.5）外，搜索主路径也复用本函数：首次搜索时随
    输出携带 first_run_invite 邀请信号并落标记（对不执行任何钩子的宿主是
    唯一可靠触发链，Agent 必然处理搜索输出）。
    """
    # 清理旧版整机全局标记（自测残留会挡住重装邀请）
    try:
        LEGACY_FIRST_RUN_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        if FIRST_RUN_FILE.exists():
            return {"should_invite": False}
        if (DIGEST_DIR / "first_run_fallback_invited").exists():
            return {"should_invite": False}
    except OSError:
        return {"should_invite": False}
    written = False
    try:
        FIRST_RUN_FILE.write_text(date.today().isoformat() + "\n", encoding="utf-8")
        written = True
    except OSError:
        pass
    if not written:
        try:
            DIGEST_DIR.mkdir(parents=True, exist_ok=True)
            (DIGEST_DIR / "first_run_fallback_invited").write_text(
                date.today().isoformat() + "\n", encoding="utf-8")
        except OSError:
            pass
    return {"should_invite": True}


def digest(keywords: list, record: bool = True) -> dict:
    """周报推荐数据：技能/作品分路逐关键词取 Top1 + GitHub 榜各随机 1 条，冷却去重。

    - 技能路：每个关键词跑一次语义搜索，仅取第 1 名（跳过冷却期内已推过的）
    - 作品路：每个关键词跑一次作品关键词搜索，仅取第 1 条已发布作品
      （未关联 skill 的独立作品同样能命中）
    - 热门补充：仅 GitHub 近期飙升榜，随机取 2 条（累计高星榜不采用，避免重复推同一批）
    """
    keywords = [k.strip() for k in keywords if k and k.strip()][:3]
    hist = _load_digest_history()
    output = {"keywords": keywords, "skills": [], "works": [], "hot": []}
    used_skills = set(hist["skills"])

    for kw in keywords:
        # 技能路：语义搜索 Top1
        try:
            skills, _, err = search_deep(kw)
        except Exception:
            skills, err = [], True
        if not err:
            for s in skills:
                name = s.get("name", "")
                if name and name not in used_skills:
                    used_skills.add(name)
                    output["skills"].append({
                        "keyword": kw,
                        "name": name,
                        "reason": _compress_note(s.get("description")) or "相关技能推荐",
                        "downloadCount": s.get("downloadCount", 0),
                        "url": RANK_ENTRY_URL.format(name=urllib.parse.quote(name)),
                    })
                    break
        # 作品路：keyword 搜索 Top1（未关联 skill 的独立作品也能命中）
        try:
            data = _fetch_json(f"/creations?keyword={urllib.parse.quote(kw)}&pageSize=20&page=1")
        except Exception:
            data = None
        lst = (data or {}).get("list") or [] if isinstance(data, dict) else []
        for it in lst:
            if not isinstance(it, dict) or it.get("status", "published") != "published":
                continue
            wid = it.get("id", "")
            if not wid or wid in hist["works"]:
                continue
            output["works"].append({
                "keyword": kw,
                "id": wid,
                "title": (it.get("title") or "").strip(),
                "summary": _compress_note(it.get("description")),
                "platform": it.get("externalPlatform") or "",
                "skillName": it.get("skillName") or "",
                "url": WORK_URL.format(id=wid),
            })
            break

    # 热门补充：仅 GitHub 近期飙升榜，随机取 2 条，带一句话介绍
    for kind in DIGEST_BOARDS:
        reg = RANK_REGISTRY[kind]
        try:
            data = _fetch_json(reg["url"])
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        entries = [it for it in data
                   if isinstance(it, dict) and it.get("name") and it.get("name") not in used_skills]
        if not entries:
            continue
        for it in random.sample(entries, min(DIGEST_HOT_COUNT, len(entries))):
            used_skills.add(it["name"])
            output["hot"].append({
                "board": "GitHub 趋势榜·近期飙升" if kind == "github_star_delta" else reg["title"],
                "name": it["name"],
                "metric": "⭐ " + _format_count(it.get("downloadCount", 0)),
                "note": _compress_note(it.get("description")),
                "url": RANK_ENTRY_URL.format(name=urllib.parse.quote(it["name"])),
            })

    if record:
        _record_digest_history([s["name"] for s in output["skills"]],
                               [w["id"] for w in output["works"]])
    return output


def check_version():
    """输出版本检查结果 JSON：{current_version, latest_version, update_available}"""
    current = get_skill_version()
    latest = "unknown"
    try:
        api_url = "https://api.github.com/repos/wheelry/deep-skill-finder/contents/SKILL.md"
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "deep-skill-finder/1.0"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            import base64
            d = json.loads(resp.read())
            content = base64.b64decode(d["content"]).decode()
            m = re.search(r'version:\s*"([^"]+)"', content)
            if m:
                latest = m.group(1)
    except Exception:
        pass

    def parse_ver(v):
        try:
            return tuple(int(x) for x in v.split("."))
        except Exception:
            return (0,)

    update = latest != "unknown" and parse_ver(current) < parse_ver(latest)
    print(json.dumps({"current_version": current, "latest_version": latest, "update_available": update}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="搜索 Meyo 社区 Skill")
    parser.add_argument("query", nargs="?", help="搜索关键词或任务描述")
    parser.add_argument("--agent-type", default=None, help="当前 Agent 类型（如 openclaw/hermes/qclaw/catdesk 等，可选）")
    parser.add_argument("--output", help="输出 JSON 到文件（默认 stdout）")
    parser.add_argument("--check-version", action="store_true", help="检查是否有新版本")
    parser.add_argument("--case-check", metavar="SKILLS", help="对逗号分隔的技能名列表做案例展示探测（作品/评价/榜单三级降级，返回 JSON）")
    parser.add_argument("--digest", metavar="KEYWORDS", help="按逗号分隔的工作关键词生成周报推荐数据（技能/作品分路 Top1 + 飙升榜随机 2 条，去重后返回 JSON）")
    parser.add_argument("--no-record", action="store_true", help="--digest 只生成不记录历史（测试用）")
    parser.add_argument("--first-run-check", action="store_true", help="首次加载自检：返回是否应发出每周技能推荐邀请（自动落一次性标记）")
    args = parser.parse_args()

    if args.check_version:
        check_version()
        return

    if args.case_check:
        result = case_check([n for n in args.case_check.split(",")])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.first_run_check:
        print(json.dumps(first_run_check(), ensure_ascii=False))
        return 0

    if args.digest:
        result = digest([k for k in args.digest.split(",")], record=not args.no_record)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not args.query:
        parser.error("请提供搜索关键词")

    deep_results, request_id, search_error = search_deep(args.query, agent_type=args.agent_type)

    output = {
        "community": deep_results,
        "requestId": request_id,
        "searchMethods": {
            "deep": len(deep_results),
        },
    }
    if search_error:
        output["error"] = search_error

    # 首次使用携带周报邀请信号（对安装期钩子全部失效的宿主是唯一可靠触发链）：
    # 随搜索输出附带 first_run_invite，宿主 Agent 读到即按规则 8 展示配置卡。
    # 搜索输出必然被 Agent 处理，此处同时落一次性标记（与"仅此一次"原则一致）。
    try:
        if search_error is None:
            invite = first_run_check()
            if invite.get("should_invite"):
                output["first_run_invite"] = True
    except Exception:
        pass

    # 保存结果（供 install 脚本读取 requestId 串联下载链路）
    output_path = args.output or str(Path(tempfile.gettempdir()) / "deep_search_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 同时输出到 stdout
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if search_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
