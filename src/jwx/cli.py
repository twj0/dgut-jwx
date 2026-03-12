from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

from .client import JwxClient
from .client import JwxAuthError
from .config import DEFAULT_BASE_URL, load_cookie_value
from .scheduler import run_polling, sleep_until


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--cookie", default=None, help="Value of bzb_jsxsd")
    parser.add_argument(
        "--cookie-file",
        default=None,
        help="cookie.json/cookie.jsonc/cookie.jsonl/cookie.txt path",
    )
    parser.add_argument("--batch-id", default=None, help="jx0502zbid")
    parser.add_argument("--isallsc", default="", help="isallsc (usually empty)")
    parser.add_argument("--timeout", type=float, default=15.0)


def _resolve_cookie(args: argparse.Namespace) -> str:
    if args.cookie and str(args.cookie).strip():
        return str(args.cookie).strip()
    return load_cookie_value(args.cookie_file)


def cmd_courses_list(args: argparse.Namespace) -> int:
    cookie_value = _resolve_cookie(args)
    try:
        with JwxClient(base_url=args.base_url, cookie_value=cookie_value, timeout_s=args.timeout) as client:
            batch_id = args.batch_id or os.getenv("JWX_BATCH_ID")
            if batch_id:
                client.init_batch(batch_id, isallsc=args.isallsc)

            result = client.list_courses(
                display_start=args.start,
                display_length=args.length,
                s_echo=args.echo,
                query_params={"kcxx": args.kcxx or "", "skls": args.skls or ""},
            )
    except JwxAuthError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    rows = result.get("aaData") or []
    for row in rows:
        kcmc = row.get("kcmc", "")
        skls = row.get("skls", "")
        xf = row.get("xf", "")
        syrs = row.get("syrs", "")
        kcid = row.get("kcid") or row.get("jx02id") or ""
        jx0404id = row.get("jx0404id", "")
        print(f"{kcmc}\t{skls}\t{xf}\t{syrs}\t{kcid}\t{jx0404id}")
    return 0


def cmd_courses_selected(args: argparse.Namespace) -> int:
    cookie_value = _resolve_cookie(args)
    try:
        with JwxClient(base_url=args.base_url, cookie_value=cookie_value, timeout_s=args.timeout) as client:
            if args.json:
                items = client.list_selected_courses()
                print(json.dumps([item.__dict__ for item in items], ensure_ascii=False, indent=2))
                return 0
            html = client.get_selected_courses_html()
    except JwxAuthError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    sys.stdout.write(html)
    return 0


def cmd_select(args: argparse.Namespace) -> int:
    cookie_value = _resolve_cookie(args)
    try:
        with JwxClient(base_url=args.base_url, cookie_value=cookie_value, timeout_s=args.timeout) as client:
            batch_id = args.batch_id or os.getenv("JWX_BATCH_ID")
            if batch_id:
                client.init_batch(batch_id, isallsc=args.isallsc)
            result = client.select_course(kcid=args.kcid, jx0404id=args.jx0404id)
    except JwxAuthError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(result.get("message", result))
    return 0 if result.get("success") is True else 1


def cmd_drop(args: argparse.Namespace) -> int:
    cookie_value = _resolve_cookie(args)
    try:
        with JwxClient(base_url=args.base_url, cookie_value=cookie_value, timeout_s=args.timeout) as client:
            result = client.drop_selected_course(jx0404id=args.jx0404id)
    except JwxAuthError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(result.get("message", result))
    return 0 if result.get("success") is True else 1


def _as_float(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:  # noqa: BLE001
        return None


def _as_int(value) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except Exception:  # noqa: BLE001
        return None


def _is_conflict(course: dict) -> bool:
    cfbs = course.get("cfbs")
    if cfbs not in (None, "null"):
        return True
    ctsm = course.get("ctsm")
    return bool(ctsm)


def cmd_auto_select(args: argparse.Namespace) -> int:
    cookie_value = _resolve_cookie(args)
    try:
        with JwxClient(base_url=args.base_url, cookie_value=cookie_value, timeout_s=args.timeout) as client:
            batch_id = args.batch_id or os.getenv("JWX_BATCH_ID")
            if batch_id:
                client.init_batch(batch_id, isallsc=args.isallsc)

            s_echo = args.echo
            candidates: list[dict] = []
            display_start = args.start
            for _ in range(args.pages):
                result = client.list_courses(
                    display_start=display_start,
                    display_length=args.length,
                    s_echo=s_echo,
                    query_params={"kcxx": args.kcxx or "", "skls": args.skls or ""},
                )
                rows = result.get("aaData") or []
                candidates.extend(rows)
                if len(rows) < args.length:
                    break
                display_start += args.length
                s_echo += 1
    except JwxAuthError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

        max_xf = args.max_xf
        min_seats = args.min_seats

        filtered: list[dict] = []
        for course in candidates:
            xf = _as_float(course.get("xf"))
            if xf is not None and xf > max_xf:
                continue

            syrs = _as_int(course.get("syrs"))
            if syrs is not None and syrs < min_seats:
                continue

            if not args.allow_conflict and _is_conflict(course):
                continue

            sfkfxk = course.get("sfkfxk")
            if sfkfxk not in (None, "", "1"):
                continue

            filtered.append(course)

        if not filtered:
            print("未找到满足条件的课程", file=sys.stderr)
            return 2

        chosen = filtered[0]
        kcmc = chosen.get("kcmc", "")
        skls = chosen.get("skls", "")
        xf = chosen.get("xf", "")
        syrs = chosen.get("syrs", "")
        kcid = chosen.get("kcid") or chosen.get("jx02id") or ""
        jx0404id = chosen.get("jx0404id", "")
        print(f"选择: {kcmc} / {skls} / xf={xf} / syrs={syrs}")
        print(f"kcid={kcid} jx0404id={jx0404id}")

        if args.dry_run:
            return 0

        result = client.select_course(kcid=kcid, jx0404id=jx0404id)

    print(result.get("message", result))
    return 0 if result.get("success") is True else 1


def _parse_at(value: str) -> datetime:
    value = value.strip()
    if value.isdigit():
        return datetime.fromtimestamp(int(value))
    return datetime.fromisoformat(value)


def cmd_schedule_select(args: argparse.Namespace) -> int:
    cookie_value = _resolve_cookie(args)
    at = _parse_at(args.at) if args.at else None

    if at is not None:
        sleep_until(at)

    try:
        with JwxClient(base_url=args.base_url, cookie_value=cookie_value, timeout_s=args.timeout) as client:
            batch_id = args.batch_id or os.getenv("JWX_BATCH_ID")
            if batch_id:
                client.init_batch(batch_id, isallsc=args.isallsc)

            def action():
                result = client.select_course(kcid=args.kcid, jx0404id=args.jx0404id)
                if result.get("success") is True:
                    return result
                raise RuntimeError(result.get("message", str(result)))

            result = run_polling(action=action, interval_s=args.interval, max_attempts=args.attempts)
    except JwxAuthError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if result.last_result is not None:
        print("选课成功")
        print(json.dumps(result.last_result, ensure_ascii=False))
        return 0

    print(f"选课失败（已重试 {result.attempts} 次）：{result.last_error}", file=sys.stderr)
    return 1


def cmd_schedule_auto(args: argparse.Namespace) -> int:
    cookie_value = _resolve_cookie(args)
    at = _parse_at(args.at) if args.at else None

    if at is not None:
        sleep_until(at)

    try:
        with JwxClient(base_url=args.base_url, cookie_value=cookie_value, timeout_s=args.timeout) as client:
            batch_id = args.batch_id or os.getenv("JWX_BATCH_ID")
            if batch_id:
                client.init_batch(batch_id, isallsc=args.isallsc)

            def action():
                result = client.list_courses(
                    display_start=args.start,
                    display_length=args.length,
                    s_echo=int(time.time()) % 100000,
                    query_params={"kcxx": args.kcxx or "", "skls": args.skls or ""},
                )
                rows = result.get("aaData") or []
                max_xf = args.max_xf
                min_seats = args.min_seats
                last_message: str | None = None
                for course in rows:
                    xf = _as_float(course.get("xf"))
                    if xf is not None and xf > max_xf:
                        continue

                    syrs = _as_int(course.get("syrs"))
                    if syrs is not None and syrs < min_seats:
                        continue

                    if not args.allow_conflict and _is_conflict(course):
                        continue

                    kcid = course.get("kcid") or course.get("jx02id")
                    jx0404id = course.get("jx0404id")
                    if not kcid or not jx0404id:
                        continue

                    sel = client.select_course(kcid=kcid, jx0404id=jx0404id)
                    if sel.get("success") is True:
                        return {"selected": course, "result": sel}
                    last_message = sel.get("message", str(sel))
                    continue

                raise RuntimeError(last_message or "未找到可选课程")

            result = run_polling(action=action, interval_s=args.interval, max_attempts=args.attempts)
    except JwxAuthError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if result.last_result is not None:
        print("选课成功")
        print(json.dumps(result.last_result, ensure_ascii=False))
        return 0

    print(f"选课失败（已重试 {result.attempts} 次）：{result.last_error}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jwx")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_courses = sub.add_parser("courses", help="Course related commands")
    sub_courses = p_courses.add_subparsers(dest="courses_cmd", required=True)

    p_list = sub_courses.add_parser("list", help="List courses (TSV by default)")
    _add_common_args(p_list)
    p_list.add_argument("--start", type=int, default=0)
    p_list.add_argument("--length", type=int, default=10)
    p_list.add_argument("--echo", type=int, default=1)
    p_list.add_argument("--kcxx", default="", help="Course/teacher keyword (server-side)")
    p_list.add_argument("--skls", default="", help="Teacher name (server-side)")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_courses_list)

    p_selected = sub_courses.add_parser("selected", help="Dump selected courses HTML")
    _add_common_args(p_selected)
    p_selected.add_argument("--json", action="store_true", help="Parse selected courses into JSON")
    p_selected.set_defaults(func=cmd_courses_selected)

    p_select = sub.add_parser("select", help="Select a specific course")
    _add_common_args(p_select)
    p_select.add_argument("--kcid", required=True)
    p_select.add_argument("--jx0404id", required=True)
    p_select.set_defaults(func=cmd_select)

    p_drop = sub.add_parser("drop", help="Drop a selected course by jx0404id")
    _add_common_args(p_drop)
    p_drop.add_argument("--jx0404id", required=True)
    p_drop.set_defaults(func=cmd_drop)

    p_auto = sub.add_parser("auto", help="Auto-pick then select")
    _add_common_args(p_auto)
    p_auto.add_argument("--kcxx", default="", help="Course/teacher keyword (server-side)")
    p_auto.add_argument("--skls", default="", help="Teacher name (server-side)")
    p_auto.add_argument("--start", type=int, default=0)
    p_auto.add_argument("--length", type=int, default=50)
    p_auto.add_argument("--pages", type=int, default=1)
    p_auto.add_argument("--echo", type=int, default=1)
    p_auto.add_argument("--max-xf", type=float, default=1.0)
    p_auto.add_argument("--min-seats", type=int, default=1)
    p_auto.add_argument("--allow-conflict", action="store_true")
    p_auto.add_argument("--dry-run", action="store_true")
    p_auto.set_defaults(func=cmd_auto_select)

    p_sched = sub.add_parser("schedule", help="Scheduled actions")
    sub_sched = p_sched.add_subparsers(dest="schedule_cmd", required=True)

    p_sched_select = sub_sched.add_parser("select", help="Select at a time, then retry")
    _add_common_args(p_sched_select)
    p_sched_select.add_argument("--kcid", required=True)
    p_sched_select.add_argument("--jx0404id", required=True)
    p_sched_select.add_argument("--at", default=None, help="ISO time or unix timestamp")
    p_sched_select.add_argument("--interval", type=float, default=0.5)
    p_sched_select.add_argument("--attempts", type=int, default=60)
    p_sched_select.set_defaults(func=cmd_schedule_select)

    p_sched_auto = sub_sched.add_parser("auto", help="Auto-pick at a time, then retry")
    _add_common_args(p_sched_auto)
    p_sched_auto.add_argument("--kcxx", default="", help="Course/teacher keyword (server-side)")
    p_sched_auto.add_argument("--skls", default="", help="Teacher name (server-side)")
    p_sched_auto.add_argument("--start", type=int, default=0)
    p_sched_auto.add_argument("--length", type=int, default=50)
    p_sched_auto.add_argument("--max-xf", type=float, default=1.0)
    p_sched_auto.add_argument("--min-seats", type=int, default=1)
    p_sched_auto.add_argument("--allow-conflict", action="store_true")
    p_sched_auto.add_argument("--at", default=None, help="ISO time or unix timestamp")
    p_sched_auto.add_argument("--interval", type=float, default=0.5)
    p_sched_auto.add_argument("--attempts", type=int, default=60)
    p_sched_auto.set_defaults(func=cmd_schedule_auto)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
