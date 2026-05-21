#!/usr/bin/env python3
"""最小测试脚本：取最近一张照片 -> 发给模型 -> 打印描述和关键词"""

from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from datetime import datetime

import requests

from runtime_config import ConfigError, RuntimeConfig, load_runtime_config


def get_latest_photo():
    import osxphotos

    db = osxphotos.PhotosDB()

    photos = sorted(db.photos(), key=lambda p: p.date or datetime.min, reverse=True)
    if not photos:
        print("⚠️  照片库为空")
        sys.exit(1)

    for p in photos:
        if p.ismovie:
            continue
        print(f"✅ 选中照片: {p.filename or 'unknown'}")
        print(f"   日期: {p.date}")
        print(f"   UUID: {p.uuid}")
        print(f"   本地原图: {'✅ 已下载' if not p.ismissing else '☁️  iCloud 未下载'}")
        return p

    print("⚠️  未找到可用的照片")
    sys.exit(1)


def get_image_path(photo):
    if not photo.ismissing:
        tmpdir = tempfile.mkdtemp(prefix="photo_analyze_")
        exported = photo.export(tmpdir)
        path = exported[0] if isinstance(exported, list) else exported
        source = "原图"
    elif photo.path_derivatives:
        path = photo.path_derivatives[0]
        source = "本地预览(缩略图)"
    else:
        print("⚠️  既无本地原图也无预览副本")
        sys.exit(1)

    print(f"📁 使用 {source}: {path}")
    return path, source


def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def prompt_text():
    return (
        "只返回一个合法 JSON 对象，不要 Markdown，不要解释，不要多余文字。"
        "JSON 必须包含 description 和 keywords 两个字段。"
        "description 用中文写 120-160 字，适合相册检索和回忆；说明画面主体、动作关系、场景、重要物体、颜色、光线、氛围和可搜索细节。"
        "不要编造不确定内容，可用“像是”“可能”。"
        "keywords 是 8-12 个中文短词数组，不能为空。"
        '格式必须严格如下：{"description":"描述","keywords":["关键词1","关键词2"]}'
    )


def analyze_with_model(cfg: RuntimeConfig, image_path):
    print("🤖 发送给模型推理...")
    b64 = encode_image(image_path)

    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg", ".heic") else "image/png"

    payload = {
        "model": cfg.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text(),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": cfg.max_tokens,
        "response_format": {"type": "json_object"},
    }

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
    text = response["choices"][0]["message"]["content"]
    print(f"📝 模型原始回复:\n{text}\n")

    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
        text = text.strip()
    if text.startswith("json"):
        text = text[4:].strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        print("⚠️  模型返回的不是合法 JSON，已保存原始回复")
        raw_path = "/tmp/photo_analyze_raw_response.txt"
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"   原始回复已保存到: {raw_path}")
        return None

    return result


def main():
    print("=" * 60)
    print("📸 Photo Analyzer — 最小测试脚本")
    print("=" * 60)

    try:
        cfg = load_runtime_config()
    except ConfigError as e:
        print(f"❌ 配置错误: {e}")
        return 2

    print(f"🔧 模型: {cfg.model}")
    print(f"🔗 接口: {cfg.api_url}")

    photo = get_latest_photo()
    image_path, source = get_image_path(photo)

    try:
        response = analyze_with_model(cfg, image_path)
        result = parse_result(response)

        if result:
            print()
            print("-" * 60)
            print(f"📋 生成结果 (来自{source})")
            print(f"描述: {result.get('description', 'N/A')}")
            print(f"关键词: {', '.join(result.get('keywords', []))}")
            print("-" * 60)
    finally:
        if image_path.startswith("/tmp/") and os.path.isfile(image_path):
            os.remove(image_path)
            parent = os.path.dirname(image_path)
            if os.path.isdir(parent):
                try:
                    os.rmdir(parent)
                except OSError:
                    pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
