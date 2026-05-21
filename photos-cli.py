#!/usr/bin/env -S uv run python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["osxphotos"]
# ///
"""photos-cli.py — 读取 Photos.app 照片元数据的命令行工具

另一个 Agent 可通过此工具浏览你的相册内容（仅读元数据，不读图片）。
"""

import argparse
import json
import random
import sys
from datetime import datetime, timedelta

import osxphotos

OUTPUT_FORMAT = "text"
LIMIT = 20

# ── 输出辅助 ──────────────────────────────────────────

def _trunc(s, n=60):
    s = s or ""
    return s if len(s) <= n else s[: n - 1] + "…"


def fmt_date(d):
    if d is None:
        return "????-??-??"
    return d.strftime("%Y-%m-%d %H:%M")


def _frac(ss):
    """将快门秒数转为分数形式，如 0.06666667 -> 1/15"""
    if not ss or ss <= 0:
        return None
    if ss >= 1:
        return f"{ss:.1f}s"
    denom = round(1 / ss)
    if abs(ss - 1 / denom) < 0.0005:
        return f"1/{denom}"
    return f"1/{denom}"


def fmt_exif_compact(exif):
    """紧凑器材一行，如: 📱 iPhone 16 · f/1.6 · 1/60 · ISO400 · 5.96mm"""
    if not exif:
        return None
    parts = []
    cam = exif.camera_model
    if cam:
        parts.append(f"📱 {cam}")
    ap = exif.aperture
    if ap:
        parts.append(f"f/{ap:.1f}".rstrip("0").rstrip("."))
    ss = _frac(exif.shutter_speed)
    if ss:
        parts.append(ss)
    iso = exif.iso
    if iso:
        parts.append(f"ISO{iso}")
    fl = exif.focal_length
    if fl:
        parts.append(f"{fl:.0f}mm")
    return " · ".join(parts) if parts else None


def fmt_exif_detail(exif):
    """详细 EXIF 多行文本"""
    if not exif:
        return ["    器材信息: (无)"]
    lines = []
    if exif.camera_make or exif.camera_model:
        make = f"{exif.camera_make} " if exif.camera_make else ""
        model = exif.camera_model or ""
        lines.append(f"    相机: {make}{model}")
    if exif.lens_model:
        lines.append(f"    镜头: {exif.lens_model}")
    if exif.focal_length:
        lines.append(f"    焦距: {exif.focal_length:.1f}mm")
    if exif.aperture:
        lines.append(f"    光圈: f/{exif.aperture:.1f}".rstrip("0").rstrip("."))
    ss = _frac(exif.shutter_speed)
    if ss:
        lines.append(f"    快门: {ss}")
    if exif.iso:
        lines.append(f"    ISO: {exif.iso}")
    if exif.exposure_bias is not None:
        lines.append(f"    曝光补偿: {exif.exposure_bias:+.2f}")
    if exif.flash_fired is not None:
        lines.append(f"    闪光灯: {'是' if exif.flash_fired else '否'}")
    if exif.white_balance is not None:
        lines.append(f"    白平衡: {exif.white_balance}")
    if exif.metering_mode is not None:
        mm = {1: "平均", 2: "中央重点", 3: "点测光", 4: "多点", 5: "评价测光"}.get(exif.metering_mode, str(exif.metering_mode))
        lines.append(f"    测光: {mm}")
    return lines if lines else ["    器材信息: (无)"]


# ── 普通数据 ──────────────────────────────────────────

def photo_to_dict(p):
    """将 PhotoInfo 转为 JSON 友好 dict，含 EXIF"""
    exif = p.exif_info
    d = {
        "uuid": p.uuid,
        "filename": p.filename,
        "date": p.date.isoformat() if p.date else None,
        "description": p.description,
        "keywords": p.keywords or [],
        "width": p.width,
        "height": p.height,
        "favorite": p.favorite,
        "ismissing": p.ismissing,
        "ismovie": p.ismovie,
        "location": f"{p.latitude},{p.longitude}" if p.latitude else None,
    }
    if exif:
        d["exif"] = {
            "camera_make": exif.camera_make,
            "camera_model": exif.camera_model,
            "lens_model": exif.lens_model,
            "focal_length": exif.focal_length,
            "aperture": exif.aperture,
            "shutter_speed": exif.shutter_speed,
            "iso": exif.iso,
            "exposure_bias": exif.exposure_bias,
            "flash_fired": exif.flash_fired,
            "white_balance": exif.white_balance,
            "metering_mode": exif.metering_mode,
        }
    return d


def _info(msg):
    """打印信息 — JSON 模式下走 stderr"""
    dest = sys.stderr if OUTPUT_FORMAT == "json" else sys.stdout
    print(msg, file=dest)


def output_photos(photos, detailed=False):
    if OUTPUT_FORMAT == "json":
        items = [photo_to_dict(p) for p in photos]
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return

    for i, p in enumerate(photos, 1):
        date_str = fmt_date(p.date)
        kw = ", ".join(p.keywords) if p.keywords else "—"
        label = "⭐ " if p.favorite else ""
        src = "☁️" if p.ismissing else "📷"
        if p.ismovie:
            src = "🎬"
        exif_compact = fmt_exif_compact(p.exif_info)

        if detailed:
            print(f"  {src} #{i}  {label}{date_str}")
            print(f"    UUID: {p.uuid}")
            print(f"    文件: {p.original_filename or p.filename}")
            print(f"    尺寸: {p.width}x{p.height}")
            if p.latitude:
                print(f"    位置: {p.latitude:.4f}, {p.longitude:.4f}")
            for line in fmt_exif_detail(p.exif_info):
                print(line)
            print(f"    描述: {p.description or '(无)'}")
            print(f"    关键词: {kw}")
        else:
            desc = _trunc(p.description, 60)
            print(f"  {src} #{i:<3} {label}{date_str}  |  {kw}")
            if desc:
                print(f"       {desc}")
            if exif_compact:
                print(f"       {exif_compact}")
            print(f"       UUID: {p.uuid[:8]}")


def cmd_latest(db, args):
    photos = sorted(
        [p for p in db.photos() if not p.ismovie],
        key=lambda p: p.date or datetime.min,
        reverse=True,
    )[: args.n]
    _info(f"📸 最近 {len(photos)} 张照片（共 {len(db.photos())} 张）\n")
    output_photos(photos, detailed=args.detail)


def cmd_random(db, args):
    photos = [p for p in db.photos() if not p.ismovie and p.description]
    if len(photos) > args.n:
        photos = random.sample(photos, args.n)
    _info(f"🎲 随机 {len(photos)} 张已标注照片\n")
    output_photos(photos, detailed=args.detail)


def cmd_search(db, args):
    term = args.term.lower()
    results = []
    for p in db.photos():
        if p.ismovie:
            continue
        desc = (p.description or "").lower()
        kw = " ".join(k.lower() for k in (p.keywords or []))
        exif_text = ""
        if p.exif_info:
            ei = p.exif_info
            exif_text = " ".join(str(x).lower() for x in [
                ei.camera_make or "", ei.camera_model or "", ei.lens_model or ""
            ])
        if term in desc or term in kw or term in exif_text or term in (p.original_filename or p.filename or "").lower():
            results.append(p)
    results.sort(key=lambda p: p.date or datetime.min, reverse=True)
    results = results[: args.n]
    _info(f"🔍 搜索「{args.term}」— 找到 {len(results)} 张\n")
    output_photos(results, detailed=args.detail)


def cmd_show(db, args):
    for p in db.photos():
        if p.uuid.startswith(args.uuid) or p.uuid == args.uuid:
            output_photos([p], detailed=True)
            return
    print(f"❌ 未找到 UUID: {args.uuid}")


def cmd_stats(db):
    all_photos = [p for p in db.photos() if not p.ismovie]
    with_desc = [p for p in all_photos if p.description]
    with_kw = [p for p in all_photos if p.keywords]
    favorites = [p for p in all_photos if p.favorite]
    missing = [p for p in all_photos if p.ismissing]

    dates = [p.date for p in all_photos if p.date]
    kw_counter = {}
    for p in with_kw:
        for k in p.keywords:
            kw_counter[k] = kw_counter.get(k, 0) + 1
    top_kw = sorted(kw_counter.items(), key=lambda x: x[1], reverse=True)[:15]

    _info(f"📊 Photos.app 相册统计")
    _info(f"  总照片数: {len(all_photos)}")
    _info(f"  已有描述: {len(with_desc)} ({len(with_desc)*100//max(1,len(all_photos))}%)")
    _info(f"  已有关键词: {len(with_kw)} ({len(with_kw)*100//max(1,len(all_photos))}%)")
    _info(f"  收藏: {len(favorites)}")
    _info(f"  iCloud 未下载: {len(missing)}")
    if dates:
        _info(f"  时间范围: {min(dates):%Y-%m-%d} ~ {max(dates):%Y-%m-%d}")
    if top_kw:
        kw_list = ", ".join(f"{k}({v})" for k, v in top_kw)
        _info(f"  热门关键词: {kw_list}")


def cmd_keywords(db, args):
    kw_counter = {}
    for p in db.photos():
        for k in p.keywords or []:
            kw_counter[k] = kw_counter.get(k, 0) + 1
    top = sorted(kw_counter.items(), key=lambda x: x[1], reverse=True)[: args.n]
    for k, v in top:
        _info(f"  {v:4d}  {k}")


def cmd_dated(db, args):
    target = datetime.strptime(args.date, "%Y-%m-%d").date()
    start = datetime(target.year, target.month, target.day)
    end = start + timedelta(days=1)
    photos = [p for p in db.photos() if not p.ismovie and p.date and start <= p.date < end]
    photos.sort(key=lambda p: p.date or datetime.min)
    _info(f"📅 {args.date} — {len(photos)} 张照片\n")
    output_photos(photos, detailed=args.detail)


# ── 主入口 ────────────────────────────────────────────

def main():
    global OUTPUT_FORMAT, LIMIT

    parser = argparse.ArgumentParser(
        description="Photos.app 元数据查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s latest          # 最近 10 张
  %(prog)s latest -n 30    # 最近 30 张
  %(prog)s random -n 5     # 随机 5 张已标注的
  %(prog)s search 骑行     # 搜索含「骑行」的
  %(prog)s show abc123     # 查看某张详情 (UUID 前缀)
  %(prog)s stats           # 相册统计
  %(prog)s keywords -n 20  # Top 20 关键词
  %(prog)s dated 2026-05-15  # 某天的照片
""",
    )
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    sub = parser.add_subparsers(dest="cmd", help="命令")

    p_latest = sub.add_parser("latest", help="最近照片")
    p_latest.add_argument("-n", type=int, default=10, help="数量 (默认 10)")
    p_latest.add_argument("--detail", action="store_true", help="显示详细信息")

    p_random = sub.add_parser("random", help="随机选择已标注照片")
    p_random.add_argument("-n", type=int, default=5, help="数量 (默认 5)")
    p_random.add_argument("--detail", action="store_true")

    p_search = sub.add_parser("search", help="搜索描述和关键词")
    p_search.add_argument("term", help="搜索词")
    p_search.add_argument("-n", type=int, default=20)
    p_search.add_argument("--detail", action="store_true")

    p_show = sub.add_parser("show", help="查看单张照片详情")
    p_show.add_argument("uuid", help="UUID 或前缀")

    sub.add_parser("stats", help="相册统计")

    p_kw = sub.add_parser("keywords", help="查看关键词")
    p_kw.add_argument("-n", type=int, default=30)

    p_date = sub.add_parser("dated", help="某天的照片")
    p_date.add_argument("date", help="日期 (YYYY-MM-DD)")
    p_date.add_argument("-n", type=int, default=50)
    p_date.add_argument("--detail", action="store_true")

    args = parser.parse_args()

    if args.json:
        OUTPUT_FORMAT = "json"

    db = osxphotos.PhotosDB()

    if args.cmd == "latest":
        cmd_latest(db, args)
    elif args.cmd == "random":
        cmd_random(db, args)
    elif args.cmd == "search":
        cmd_search(db, args)
    elif args.cmd == "show":
        cmd_show(db, args)
    elif args.cmd == "stats":
        cmd_stats(db)
    elif args.cmd == "keywords":
        cmd_keywords(db, args)
    elif args.cmd == "dated":
        cmd_dated(db, args)
    else:
        # 默认显示 help
        parser.print_help()


if __name__ == "__main__":
    main()
