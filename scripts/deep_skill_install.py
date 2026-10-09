#!/usr/bin/env python3
"""从 Meyo 社区安装 Skill。

用法:
  deep_skill_install.py <skill-name> --dir <当前 Agent 的 skills 目录>   # 安装
  deep_skill_install.py <skill-name> --dir <dir> --uninstall             # 卸载
  deep_skill_install.py --dir <dir> --list                               # 列出已安装
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

# Windows 控制台默认 cp936，中文/emoji 会 UnicodeEncodeError，统一切到 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 项目 skills/ 目录（内置 skill 来源）
_PROJECT_SKILLS_DIR = Path(__file__).resolve().parent.parent.parent

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


def _is_builtin_skill(skill_name: str) -> bool:
    """检查是否为内置 skill（项目 skills/ 目录下存在同名目录）。"""
    return (_PROJECT_SKILLS_DIR / skill_name / "SKILL.md").exists()

def _read_json(path: Path) -> dict:
    try:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def get_api_url_candidates():
    """返回 API URL 候选列表（优先级从高到低）。"""
    candidates = []

    env_urls = os.environ.get("MEYO_API_URL", "")
    for u in env_urls.split(","):
        u = u.strip().rstrip("/")
        if u:
            candidates.append(u)

    app_config = _read_json(Path.home() / ".meyo_agent" / "app.config.json")
    configured = app_config.get("settings", {}).get("meyoApiUrl", "")
    if configured:
        candidates.append(configured.rstrip("/"))

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

    _resolved_api_url = candidates[0]
    return _resolved_api_url


def get_api_token():
    app_config = _read_json(Path.home() / ".meyo_agent" / "app.config.json")
    settings = app_config.get("settings", {})
    return settings.get("meyoApiKey") or settings.get("meyoToken") or os.environ.get("MEYO_API_KEY", "")


def api_request(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """发送 API 请求，返回 JSON 响应。"""
    api_url = get_api_url()
    url = f"{api_url}/{endpoint.lstrip('/')}"
    token = get_api_token()

    headers = {"User-Agent": "deep-skill-finder/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = None
    if data:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"code": e.code, "error": True, "message": e.reason}
    except urllib.error.URLError as e:
        return {"code": 0, "error": True, "message": str(e.reason)}
    except Exception as e:
        return {"code": 0, "error": True, "message": str(e)}


def get_skill_metadata(skill_name: str) -> dict:
    """从 Meyo API 获取 skill 元数据。"""
    result = api_request(f"/skills/{urllib.parse.quote(skill_name)}")
    if result.get("code") == 200:
        return result.get("data", {})
    return {}


def _auth_headers() -> dict:
    """构造下载请求的通用 headers（含 clientId）。"""
    token = get_api_token()
    headers = {"User-Agent": "deep-skill-finder/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    client_id = get_client_id()
    if client_id:
        headers["X-Client-Id"] = client_id
    return headers


def write_origin_metadata(skill_dir: Path, skill_name: str, metadata: dict):
    """写入安装来源元数据。"""
    origin_dir = skill_dir / ".meyo"
    origin_dir.mkdir(exist_ok=True)
    origin = {
        "slug": skill_name,
        "skillId": metadata.get("id", ""),
        "installedVersion": _get_version(metadata),
        "registry": "meyo-community",
        "sourceUrl": metadata.get("sourceUrl", ""),
        "installedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(origin_dir / "origin.json", "w", encoding="utf-8") as f:
        json.dump(origin, f, ensure_ascii=False, indent=2)


def _get_version(metadata: dict) -> str:
    """从元数据提取版本号。"""
    version = metadata.get("latestVersion", "")
    if version:
        return version
    versions = metadata.get("versions", [])
    if versions and isinstance(versions, list):
        return versions[0].get("version", "unknown")
    return "unknown"


def download_skill_zip(name: str, version: str = None, request_id: str = None, agent_type: str = None) -> bytes:
    """从 /skills/download/public 下载 zip 包，返回 bytes。

    request_id 用于串联 search → download 链路，未显式传入时自动从最近一次搜索结果文件读取。
    """
    if not request_id:
        request_id = _load_last_search_request_id()

    params = {"name": name, "ref": "meyo"}
    if version:
        params["version"] = version
    if request_id:
        params["requestId"] = request_id
    if agent_type:
        params["agentType"] = agent_type
    skill_version = get_skill_version()
    if skill_version != "unknown":
        params["skillVersion"] = skill_version

    api_url = get_api_url()
    url = f"{api_url}/skills/download/public?{urllib.parse.urlencode(params)}"
    headers = _auth_headers()

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def get_skill_version() -> str:
    """从 SKILL.md frontmatter 读取当前版本号。"""
    skill_md = Path(__file__).resolve().parent.parent / "SKILL.md"
    if skill_md.exists():
        m = re.search(r'version:\s*"([^"]+)"', skill_md.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return "unknown"


def _load_last_search_request_id() -> str:
    """从 deep_skill_search.py 输出的搜索结果文件中读取 requestId，用于串联下载链路。"""
    try:
        p = Path(tempfile.gettempdir()) / "deep_search_results.json"
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("requestId", "") or ""
    except (json.JSONDecodeError, OSError):
        pass
    return ""


def install_from_zip(data: bytes, skill_name: str, target_dir: Path) -> bool:
    """从 zip 数据解压安装 skill，保留目录结构。"""
    skill_dir = target_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            # 检测并去除顶层目录前缀
            names = zf.namelist()
            strip_prefix = ""
            if names and all(n.startswith(names[0].split("/")[0] + "/") for n in names if not n.endswith("/")):
                strip_prefix = names[0].split("/")[0] + "/"

            for entry in names:
                rel = entry[len(strip_prefix):] if strip_prefix else entry
                if not rel:
                    continue
                # 安全校验：拒绝路径穿越
                if rel.startswith("/") or ".." in rel.split("/"):
                    print(f"  ✗ 拒绝不安全路径: {entry}", file=sys.stderr)
                    return False
                # 校验最终路径必须落在 skill_dir 内
                out_path = (skill_dir / rel).resolve()
                if not str(out_path).startswith(str(skill_dir.resolve())):
                    print(f"  ✗ 路径越界: {entry}", file=sys.stderr)
                    return False
                if entry.endswith("/"):
                    (skill_dir / rel).mkdir(parents=True, exist_ok=True)
                else:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(zf.read(entry))

        return True
    except Exception as e:
        print(f"  ✗ zip 解压失败: {e}", file=sys.stderr)
        return False


def install_skill(skill_name: str, target_dir: Path, agent_type: str = None) -> bool:
    """安装 skill 主流程。target_dir 为当前 Agent 的 skills 目录。"""
    # 内置 skill 不允许通过脚本覆盖
    if _is_builtin_skill(skill_name):
        print(f"✗ '{skill_name}' 是内置 skill，由桌面端自动管理，无需安装", file=sys.stderr)
        return False

    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"  安装 skill '{skill_name}' 到 {target_dir}...")

    # 获取元数据（用于 version 和 skillMdContent 兜底）
    metadata = get_skill_metadata(skill_name)
    version = _get_version(metadata)

    skill_dir = target_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    success = False

    # 下载 zip 包（包含完整文件如 scripts/）；非 zip 则当作单文件 SKILL.md
    try:
        print(f"  下载 zip 包 (version={version})...", file=sys.stderr)
        data = download_skill_zip(skill_name, version if version != "unknown" else None, agent_type=agent_type)
        if data[:4] == b'PK\x03\x04':
            success = install_from_zip(data, skill_name, target_dir)
        else:
            print("  ⚠ 下载内容非 zip 格式，保存为 SKILL.md", file=sys.stderr)
            (skill_dir / "SKILL.md").write_bytes(data)
            success = True
    except Exception as e:
        print(f"  ⚠ 下载失败: {e}，回退到 skillMdContent", file=sys.stderr)

    # 回退：使用 /skills/{name} 返回的 skillMdContent（仅 SKILL.md，不含 scripts）
    if not success:
        skill_md_content = metadata.get("skillMdContent", "")
        if skill_md_content:
            (skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")
            success = True

    if not success:
        print(f"✗ 安装失败: 无法获取 skill '{skill_name}'", file=sys.stderr)
        return False

    # 写入来源元数据
    skill_dir = target_dir / skill_name
    if skill_dir.exists():
        write_origin_metadata(skill_dir, skill_name, metadata)

    # 输出结果
    result = {
        "result": "success",
        "skillName": skill_name,
        "directory": str(skill_dir),
        "version": version,
        "source": "meyo-community",
    }
    print(f"✓ Skill '{skill_name}' 安装成功!")
    print(f"  目录: {skill_dir}")
    print(f"  版本: {version}")
    # 提示宿主 Agent 执行 Step 2.5 首次加载钩子（调用 --first-run-check 判断是否追加周报邀请）
    print("__FIRST_RUN_CHECK_REQUIRED__")
    print(json.dumps(result, ensure_ascii=False))
    return True


def uninstall_skill(skill_name: str, target_dir: Path):
    """卸载 skill。target_dir 为当前 Agent 的 skills 目录。"""
    # 内置 skill 不允许卸载
    if _is_builtin_skill(skill_name):
        print(f"✗ '{skill_name}' 是内置 skill，由桌面端自动管理，无法卸载", file=sys.stderr)
        sys.exit(1)

    # 安全校验：skill_name 只含合法字符
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', skill_name):
        print(f"✗ 非法 skill 名称: '{skill_name}'", file=sys.stderr)
        sys.exit(1)
    # 校验路径必须落在 target_dir 内
    skill_dir = target_dir / skill_name
    if not str(skill_dir.resolve()).startswith(str(target_dir.resolve())):
        print(f"✗ 路径越界: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    import shutil
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
        print(f"✓ 已卸载 '{skill_name}' (删除 {skill_dir})")
    else:
        print(f"✗ Skill '{skill_name}' 未安装在 {target_dir}")
        sys.exit(1)


def list_installed(target_dir: Path):
    """列出已安装的 skill。target_dir 为当前 Agent 的 skills 目录。"""
    if not target_dir.exists():
        print(f"未找到 skills 目录: {target_dir}")
        return

    skills = []
    for d in sorted(target_dir.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            # 读取来源
            origin_file = d / ".meyo" / "origin.json"
            source = "local"
            if origin_file.exists():
                try:
                    with open(origin_file, encoding="utf-8") as f:
                        origin = json.load(f)
                        source = origin.get("registry", "unknown")
                except (json.JSONDecodeError, OSError):
                    pass
            skills.append({"name": d.name, "source": source})

    if skills:
        print(f"\n{target_dir} ({len(skills)} skills):")
        for s in skills:
            source_tag = f" ({s['source']})" if s['source'] != 'local' else ""
            print(f"  - {s['name']}{source_tag}")
    else:
        print(f"目录 {target_dir} 下未找到已安装的 skill。")


def main():
    parser = argparse.ArgumentParser(description="安装 Meyo 社区 Skill")
    parser.add_argument("skill_name", nargs="?", help="Skill 名称/slug")
    parser.add_argument("--dir", required=True, help="当前 Agent 的 skills 目录")
    parser.add_argument("--agent-type", default=None, help="当前 Agent 类型（如 openclaw/hermes/qclaw/catdesk 等，可选）")
    parser.add_argument("--uninstall", action="store_true", help="卸载 skill")
    parser.add_argument("--list", action="store_true", help="列出已安装")
    args = parser.parse_args()

    target_dir = Path(args.dir).expanduser()

    if args.list:
        list_installed(target_dir)
    elif args.skill_name:
        if args.uninstall:
            uninstall_skill(args.skill_name, target_dir)
        else:
            install_skill(args.skill_name, target_dir, agent_type=args.agent_type)
    else:
        parser.print_help()
        print("\n示例:")
        print("  deep_skill_install.py hv-analysis --dir ~/.claude/skills --agent-type openclaw")
        print("  deep_skill_install.py hv-analysis --dir ~/.claude/skills --uninstall")
        print("  deep_skill_install.py --dir ~/.claude/skills --list")


if __name__ == "__main__":
    main()
