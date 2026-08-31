#!/usr/bin/env python
"""Summarise token usage recorded in topics/*/learning-records/usage.jsonl.

  python scripts/usage_report.py                 # all topics, totals only
  python scripts/usage_report.py go-language     # per-lesson detail for one topic
  python scripts/usage_report.py --detail        # per-lesson detail for every topic
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.config import get_topics_dir  # noqa: E402

FIELDS = ("input_tokens", "output_tokens", "cache_read", "cache_creation")


def load(topic_dir):
    f = topic_dir / "learning-records" / "usage.jsonl"
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def fmt(n):
    return f"{n:,}" if n else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topic", nargs="?", help="slug; omit for all topics")
    ap.add_argument("--detail", action="store_true", help="per-item breakdown for all topics")
    args = ap.parse_args()

    topics_dir = get_topics_dir()
    slugs = [args.topic] if args.topic else sorted(
        d.name for d in topics_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
    )
    detail = args.detail or bool(args.topic)

    grand = dict.fromkeys(FIELDS, 0)
    grand_cost, grand_items, grand_failed = 0.0, 0, 0

    print(f"{'topic / item':<52}{'in':>9}{'out':>10}{'cacheR':>11}{'cacheW':>10}{'cost':>9}")
    print("-" * 101)

    for slug in slugs:
        records = load(topics_dir / slug)
        if not records:
            continue
        totals = dict.fromkeys(FIELDS, 0)
        cost = 0.0
        failed = 0

        for r in sorted(records, key=lambda r: (r.get("kind", ""), r.get("num", 0))):
            for k in FIELDS:
                totals[k] += r.get(k, 0) or 0
            cost += r.get("cost_usd") or 0.0
            if not r.get("ok", True):
                failed += 1

        print(f"{slug:<52}{fmt(totals['input_tokens']):>9}{fmt(totals['output_tokens']):>10}"
              f"{fmt(totals['cache_read']):>11}{fmt(totals['cache_creation']):>10}"
              f"{('$%.2f' % cost) if cost else '-':>9}")

        if detail:
            for r in sorted(records, key=lambda r: (r.get("kind", ""), r.get("num", 0))):
                label = f"lesson {r['num']}" if r.get("kind") == "lesson" else r.get("kind", "?")
                mark = "" if r.get("ok", True) else "  FAILED"
                est = "~" if r.get("source") == "transcript-backfill" else " "
                print(f"  {est}{label:<49}{fmt(r.get('input_tokens', 0)):>9}"
                      f"{fmt(r.get('output_tokens', 0)):>10}{fmt(r.get('cache_read', 0)):>11}"
                      f"{fmt(r.get('cache_creation', 0)):>10}"
                      f"{('$%.2f' % r['cost_usd']) if r.get('cost_usd') else '-':>9}{mark}")
            print()

        for k in FIELDS:
            grand[k] += totals[k]
        grand_cost += cost
        grand_items += len(records)
        grand_failed += failed

    print("-" * 101)
    print(f"{'TOTAL (%d items)' % grand_items:<52}{fmt(grand['input_tokens']):>9}"
          f"{fmt(grand['output_tokens']):>10}{fmt(grand['cache_read']):>11}"
          f"{fmt(grand['cache_creation']):>10}{('$%.2f' % grand_cost) if grand_cost else '-':>9}")
    if grand_failed:
        print(f"{grand_failed} failed generation(s) recorded")
    print("\n~ = backfilled from CLI transcripts (token counts only; no cost recorded)")


if __name__ == "__main__":
    main()
