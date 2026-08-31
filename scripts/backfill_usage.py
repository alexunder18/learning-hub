#!/usr/bin/env python
"""Backfill token-usage records from Claude Code CLI transcripts.

Lessons generated before usage tracking existed left their accounting in the
CLI's own session logs under ~/.claude/projects/<project>/. This reads those,
matches each session to the lesson it generated, and writes the same
learning-records/usage.jsonl entries the generator writes today.

Safe to re-run: existing backfilled records are matched by session_id and skipped.

  python scripts/backfill_usage.py            # apply
  python scripts/backfill_usage.py --dry-run  # show what would be written
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.config import get_topics_dir  # noqa: E402
from app.topics import parse_mission_file  # noqa: E402

LESSON_RE = re.compile(r"Create lesson (\d+):\s*\"?(.*?)\"?\s*$", re.M)
SLUG_RE = re.compile(r"^Slug:\s*(\S+)", re.M)
GLOSSARY_RE = re.compile(r'glossary reference document for the topic "([^"]+)"')


def transcript_dir(project_path):
    """Claude Code encodes the project path by replacing separators with dashes."""
    return Path.home() / ".claude" / "projects" / str(project_path).replace("/", "-")


def text_of(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def parse_session(path, name_to_slug):
    """Return (slug, record) for a generation session, or None."""
    info = {"input_tokens": 0, "output_tokens": 0, "cache_read": 0, "cache_creation": 0}
    kind = num = title = slug = model = None
    first_ts = None

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = entry.get("message") or {}

        if entry.get("type") == "user" and kind is None:
            body = text_of(message)
            m = LESSON_RE.search(body)
            if m:
                kind, num, title = "lesson", int(m.group(1)), m.group(2).strip()
                s = SLUG_RE.search(body)
                slug = s.group(1) if s else None
            else:
                g = GLOSSARY_RE.search(body)
                if g:
                    # The glossary prompt carries the topic's display name, not its slug.
                    kind, num, title = "glossary", 0, "Glossary"
                    slug = name_to_slug.get(g.group(1).strip().lower())

        usage = message.get("usage") or {}
        if usage:
            info["input_tokens"] += usage.get("input_tokens", 0)
            info["output_tokens"] += usage.get("output_tokens", 0)
            info["cache_read"] += usage.get("cache_read_input_tokens", 0)
            info["cache_creation"] += usage.get("cache_creation_input_tokens", 0)
        if message.get("model"):
            model = message["model"]
        if first_ts is None and entry.get("timestamp"):
            first_ts = entry["timestamp"]

    if not kind or not slug:
        return None

    return slug, {
        "at": first_ts or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        "num": num,
        "title": title,
        "provider": "claude-code",
        "model": model,
        "session_id": path.stem,
        "source": "transcript-backfill",
        **info,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tdir = transcript_dir(REPO)
    if not tdir.is_dir():
        sys.exit(f"No CLI transcripts found at {tdir}")

    topics_dir = get_topics_dir()

    name_to_slug = {}
    for d in topics_dir.iterdir():
        if d.is_dir() and not d.name.startswith("."):
            mission = parse_mission_file(d / "MISSION.md")
            if mission.get("name"):
                name_to_slug[mission["name"].strip().lower()] = d.name
            name_to_slug.setdefault(d.name.replace("-", " ").lower(), d.name)

    by_topic = {}
    for f in sorted(tdir.glob("*.jsonl")):
        parsed = parse_session(f, name_to_slug)
        if parsed:
            slug, record = parsed
            by_topic.setdefault(slug, []).append(record)

    total_written = total_skipped = 0
    for slug, records in sorted(by_topic.items()):
        topic_dir = topics_dir / slug
        if not topic_dir.is_dir():
            print(f"  ! {slug}: topic no longer on disk, skipping {len(records)} record(s)")
            continue

        records_dir = topic_dir / "learning-records"
        usage_file = records_dir / "usage.jsonl"

        seen = set()
        if usage_file.exists():
            for line in usage_file.read_text(encoding="utf-8").splitlines():
                try:
                    seen.add(json.loads(line).get("session_id"))
                except json.JSONDecodeError:
                    continue

        fresh = [r for r in records if r["session_id"] not in seen]
        skipped = len(records) - len(fresh)
        total_skipped += skipped

        fresh.sort(key=lambda r: (r["kind"], r["num"]))
        for r in fresh:
            # The transcript proves a generation ran, not that it produced the
            # artifact — mark ok by what actually landed on disk.
            if r["kind"] == "lesson":
                produced = any((topic_dir / "lessons").glob(f"{r['num']:04d}-*.html"))
            else:
                produced = (topic_dir / "reference" / "glossary.html").exists()
            r["ok"] = produced

            label = f"lesson {r['num']}" if r["kind"] == "lesson" else "glossary"
            flag = "" if produced else "  <- no artifact on disk"
            print(f"  {slug:<32} {label:<12} {r['output_tokens']:>7} out  "
                  f"{r['cache_read']:>8} cacheR  {r['session_id'][:8]}{flag}")

        if fresh and not args.dry_run:
            records_dir.mkdir(exist_ok=True)
            with usage_file.open("a", encoding="utf-8") as fh:
                for r in fresh:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        total_written += len(fresh)

    verb = "would write" if args.dry_run else "wrote"
    print(f"\n{verb} {total_written} record(s); skipped {total_skipped} already present")


if __name__ == "__main__":
    main()
