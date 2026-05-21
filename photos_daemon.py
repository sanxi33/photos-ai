#!/usr/bin/env python3
"""photos_daemon.py — 闲时自动给照片添加描述和关键词"""

from __future__ import annotations

import argparse
import base64
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import requests

from runtime_config import ConfigError, RuntimeConfig, load_runtime_config

_g_stop = False


def signal_handler(signum, frame):
    del signum, frame
    global _g_stop
    print("\n⏹  收到退出信号，处理完当前照片后退出...")
    _g_stop = True


def load_state(cfg: RuntimeConfig):
    if cfg.state_file.exists():
        with cfg.state_file.open(encoding="utf-8") as f:
            return json.load(f)
    return {"photos": {}}


def save_state(cfg: RuntimeConfig, state):
    cfg.state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = cfg.state_file.with_suffix(cfg.state_file.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, cfg.state_file)


def idle_seconds():
    try:
        import Quartz

        return Quartz.CGEventSourceSecondsSinceLastEventType(
            Quartz.kCGEventSourceStateCombinedSessionState,
            Quartz.kCGAnyInputEventType,
        )
    except Exception:
        result = subprocess.run(
            ["ioreg", "-c", "IOHIDSystem", "-r", "-d", "0"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if "HIDIdleTime" in line:
                ns = int(line.split("=")[-1].strip())
                return ns / 1_000_000_000
    return 0


def get_all_photos():
    import osxphotos

    db = osxphotos.PhotosDB()
    photos = sorted(db.photos(), key=lambda p: p.date or datetime.min, reverse=True)
    return [p for p in photos if not p.ismovie]


def get_image_path(photo):
    if photo.path_derivatives:
        for path in photo.path_derivatives:
            if path and os.path.isfile(path):
                return path, "缩略图"

    if not photo.ismissing:
        try:
            tmpdir = tempfile.mkdtemp(prefix="photos_daemon_")
            exported = photo.export(tmpdir)
            if isinstance(exported, list):
                if not exported:
                    raise FileNotFoundError("export returned empty list")
                path = exported[0]
            else:
                path = exported
            return path, "原图"
        except Exception as e:
            print(f"  ⚠️  原图导出失败 ({e})，尝试缩略图")
            try:
                os.rmdir(tmpdir)
            except OSError:
                pass
    return None, None


def prompt_text(short=False):
    if short:
        return (
            "只返回一个合法 JSON 对象，不要 Markdown，不要解释，不要多余文字。"
            "JSON 必须包含 description 和 keywords 两个字段。"
            "description 用中文写 80-120 字；keywords 是 6-10 个中文短词数组。"
            '格式必须严格如下：{"description":"描述","keywords":["关键词1","关键词2"]}'
        )
    return (
        "只返回一个合法 JSON 对象，不要 Markdown，不要解释，不要多余文字。"
        "JSON 必须包含 description 和 keywords 两个字段。"
        "description 用中文写 120-160 字，适合相册检索和回忆；说明画面主体、动作关系、场景、重要物体、颜色、光线、氛围和可搜索细节。"
        "不要编造不确定内容，可用“像是”“可能”。"
        "keywords 是 8-12 个中文短词数组，不能为空。"
        '格式必须严格如下：{"description":"描述","keywords":["关键词1","关键词2"]}'
    )


def build_payload(cfg: RuntimeConfig, image_path, short=False):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg", ".heic") else "image/png"
    return {
        "model": cfg.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text(short)},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": cfg.retry_max_tokens if short else cfg.max_tokens,
        "response_format": {"type": "json_object"},
    }


def analyze(cfg: RuntimeConfig, image_path, short=False):
    payload = build_payload(cfg, image_path, short=short)
    resp = requests.post(
        cfg.api_url,
        headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def parse_result(response):
    text = response["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    if text.startswith("json"):
        text = text[4:].strip()
    return json.loads(text)


def analyze_json(cfg: RuntimeConfig, image_path):
    response = analyze(cfg, image_path)
    try:
        return parse_result(response)
    except json.JSONDecodeError as e:
        raw = response["choices"][0]["message"]["content"].strip()
        print(f"  ⚠️  模型 JSON 不完整，重试短版: {raw[:120]}")
        response = analyze(cfg, image_path, short=True)
        try:
            return parse_result(response)
        except json.JSONDecodeError as retry_error:
            retry_error.add_note(f"first error: {e}")
            raise retry_error


def write_metadata(uuid, description, keywords):
    desc_escaped = description.replace("\\", "\\\\").replace('"', '\\"')
    kw_list = ", ".join(f'"{k}"' for k in keywords)

    script = (
        'tell application "Photos"\n'
        f'    set p to media item id "{uuid}"\n'
        f'    set description of p to "{desc_escaped}"\n'
        f'    set keywords of p to {{{kw_list}}}\n'
        "end tell"
    )

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript 写回失败: {result.stderr.strip()}")


def wait_for_idle(cfg: RuntimeConfig, oneshot=False):
    if oneshot:
        return True
    while not _g_stop:
        idle = idle_seconds()
        if idle >= cfg.idle_threshold_seconds:
            return True
        print(
            f"\r⏳ 等待空闲... (距上次操作 {int(idle)}s / 需 {cfg.idle_threshold_seconds}s)",
            end="",
        )
        sys.stdout.flush()
        time.sleep(cfg.poll_interval_seconds)
    return False


def process_photo(cfg: RuntimeConfig, photo, state):
    uuid = photo.uuid
    if uuid in state["photos"]:
        return False

    image_path, source = get_image_path(photo)
    if not image_path:
        print(f"\n⚠️  跳过 {photo.filename}: 无法获取图片")
        state["photos"][uuid] = {"error": "no image available", "skipped": True}
        save_state(cfg, state)
        return False

    print(f"\n🖼  [{uuid[:8]}] {photo.filename} ({source})")
    try:
        result = analyze_json(cfg, image_path)

        if "description" not in result or "keywords" not in result:
            print(f"⚠️  模型返回不完整: {result}")
            state["photos"][uuid] = {"error": "incomplete model output", "failed": True}
            save_state(cfg, state)
            return False

        keywords = result["keywords"]
        if not isinstance(keywords, list):
            print(f"⚠️  keywords 不是数组: {keywords}")
            state["photos"][uuid] = {"error": "keywords is not list", "failed": True}
            save_state(cfg, state)
            return False

        keywords = [str(k).strip() for k in keywords if str(k).strip()]
        if not keywords:
            print("⚠️  keywords 为空")
            state["photos"][uuid] = {"error": "empty keywords", "failed": True}
            save_state(cfg, state)
            return False

        description = str(result["description"]).strip()
        if not description:
            print("⚠️  description 为空")
            state["photos"][uuid] = {"error": "empty description", "failed": True}
            save_state(cfg, state)
            return False

        print(f"  📝 {description}")
        print(f"  🏷  {', '.join(keywords)}")

        write_metadata(uuid, description, keywords)
        print("  ✅ 已写入 Photos.app")

        state["photos"][uuid] = {
            "description": description,
            "keywords": keywords,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
        }
        save_state(cfg, state)
        return True

    except json.JSONDecodeError as e:
        print(f"  ❌ 模型返回非 JSON: {e}")
        state["photos"][uuid] = {"error": "invalid json response", "failed": True}
        save_state(cfg, state)

    except requests.RequestException as e:
        print(f"  ❌ 网络/API 错误: {e}")
        state["photos"][uuid] = {"error": str(e), "failed": True}
        save_state(cfg, state)

    except Exception as e:
        print(f"  ❌ 未知错误: {e}")
        state["photos"][uuid] = {"error": str(e), "failed": True}
        save_state(cfg, state)

    finally:
        if image_path and image_path.startswith("/tmp/"):
            try:
                os.remove(image_path)
                parent = os.path.dirname(image_path)
                if os.path.isdir(parent):
                    os.rmdir(parent)
            except OSError:
                pass

    return False


def build_banner(cfg: RuntimeConfig, state, photos):
    total = len(photos)
    done = len(state["photos"])
    failed = sum(1 for v in state["photos"].values() if v.get("failed"))
    pct = done * 100 // total if total else 0
    banner = (
        "=" * 58
        + "\n"
        + "  📸 Photos AI 标注守护进程 v1\n"
        + f"  总照片: {total}  |  已处理: {done}  |  失败: {failed}  ({pct}%)\n"
        + f"  空闲 {cfg.idle_threshold_seconds // 60} 分钟后自动开始\n"
        + f"  模型: {cfg.model}\n"
        + "  Ctrl+C 优雅退出\n"
        + "=" * 58
    )
    return banner


def main():
    global _g_stop
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description="闲时自动标注照片")
    parser.add_argument("--oneshot", action="store_true", help="忽略空闲检测，立即处理一张")
    args = parser.parse_args()

    try:
        cfg = load_runtime_config()
    except ConfigError as e:
        print(f"❌ 配置错误: {e}")
        return 2

    state = load_state(cfg)
    photos = get_all_photos()

    if not photos:
        print("📭 照片库为空")
        return 0

    total = len(photos)
    done = len(state["photos"])
    remaining = total - done
    print(build_banner(cfg, state, photos))

    if remaining == 0:
        print("\n🎉 所有照片已处理完毕！")
        return 0

    for photo in photos:
        if _g_stop:
            break
        if photo.uuid in state["photos"]:
            continue

        if not wait_for_idle(cfg, args.oneshot):
            break

        process_photo(cfg, photo, state)

        if args.oneshot:
            break

    total_done = len(state["photos"])
    print(f"\n{'=' * 58}")
    print(f"🏁 本轮结束。共已处理 {total_done}/{total} 张")
    print(f"   未处理: {total - total_done} 张")
    print(f"   状态文件: {cfg.state_file}")
    print(f"{'=' * 58}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
