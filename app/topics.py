import re
import glob
from pathlib import Path

from .config import get_topics_dir
from .generator import get_lesson_status


def parse_mission_file(mission_path):
    if not mission_path.exists():
        return {}
    text = mission_path.read_text(encoding="utf-8")
    result = {}
    name_match = re.search(r"# Mission:\s*(.+)", text)
    if name_match:
        result["name"] = name_match.group(1).strip()
    lang_match = re.search(r"## Language\s*\n(\w+)", text)
    if lang_match:
        result["language"] = lang_match.group(1).strip()
    for key, pattern in [
        ("why", r"## Why\s*\n(.+?)(?=\n##|\Z)"),
        ("icon", r"## Icon\s*\n(.+?)(?=\n##|\Z)"),
    ]:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            result[key] = m.group(1).strip()
    return result


def load_syllabus(topic_dir):
    syllabus_path = topic_dir / "SYLLABUS.md"
    if not syllabus_path.exists():
        return []
    lines = syllabus_path.read_text(encoding="utf-8").strip().split("\n")
    items = []
    for line in lines:
        m = re.match(r"\d+\.\s*(.+)", line.strip())
        if m:
            items.append(m.group(1).strip())
    return items


def get_existing_lesson_numbers(lessons_dir):
    nums = set()
    if lessons_dir.exists():
        for f in lessons_dir.glob("*.html"):
            m = re.match(r"(\d+)", f.name)
            if m:
                nums.add(int(m.group(1)))
    return nums


def get_topics():
    topics_dir = get_topics_dir()
    topics = []
    for d in sorted(topics_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        mission = parse_mission_file(d / "MISSION.md")
        syllabus = load_syllabus(d)
        lessons_dir = d / "lessons"
        reference_dir = d / "reference"

        lesson_files = sorted(glob.glob(str(lessons_dir / "*.html"))) if lessons_dir.exists() else []
        ref_files = sorted(glob.glob(str(reference_dir / "*.html"))) if reference_dir.exists() else []

        if not mission and not lesson_files:
            continue

        from .generator import is_generating
        topics.append({
            "slug": d.name,
            "name": mission.get("name", d.name.replace("-", " ").title()),
            "description": mission.get("why", ""),
            "icon": mission.get("icon", ""),
            "lesson_count": len(lesson_files),
            "syllabus_count": len(syllabus) or len(lesson_files),
            "reference_count": len(ref_files),
            "is_generating": is_generating(d.name),
        })
    return topics


def get_topic_detail(slug):
    topics_dir = get_topics_dir()
    topic_dir = topics_dir / slug
    if not topic_dir.is_dir():
        return None

    mission = parse_mission_file(topic_dir / "MISSION.md")
    syllabus = load_syllabus(topic_dir)
    lessons_dir = topic_dir / "lessons"
    reference_dir = topic_dir / "reference"
    existing_numbers = get_existing_lesson_numbers(lessons_dir)

    lesson_files = {}
    if lessons_dir.exists():
        for f in sorted(lessons_dir.glob("*.html")):
            m = re.match(r"(\d+)", f.name)
            if m:
                num = int(m.group(1))
                title = f.stem
                num_match = re.match(r"\d+-(.*)", f.stem)
                if num_match:
                    title = num_match.group(1).replace("-", " ").title()
                lesson_files[num] = {"file": f.name, "title": title}

    ref_files = []
    if reference_dir.exists():
        for f in sorted(reference_dir.glob("*.html")):
            ref_files.append({"file": f.name, "title": f.stem.replace("-", " ").title()})

    syllabus_items = []
    if syllabus:
        for i, title in enumerate(syllabus, 1):
            syllabus_items.append({
                "number": i,
                "title": title,
                "status": get_lesson_status(slug, i),
                "file": lesson_files.get(i, {}).get("file"),
            })
    else:
        for num in sorted(existing_numbers):
            lf = lesson_files.get(num, {})
            syllabus_items.append({
                "number": num,
                "title": lf.get("title", f"Lesson {num}"),
                "status": "completed",
                "file": lf.get("file"),
            })

    return {
        "slug": slug,
        "name": mission.get("name", slug.replace("-", " ").title()),
        "mission_why": mission.get("why", ""),
        "language": mission.get("language", "en"),
        "syllabus": syllabus_items,
        "references": ref_files,
    }


def write_mission_file(topic_dir, mission):
    content = f"# Mission: {mission['topic_name']}\n\n## Why\n{mission['why']}\n\n## Success looks like\n"
    for c in mission.get("success_criteria", []):
        content += f"- {c}\n"
    content += "\n## Constraints\n- Self-paced, online learning\n\n## Out of scope\n"
    for o in mission.get("out_of_scope", []):
        content += f"- {o}\n"
    if mission.get("prior_knowledge"):
        content += f"\n## Prior knowledge\n{mission['prior_knowledge']}\n"
    if mission.get("language"):
        content += f"\n## Language\n{mission['language']}\n"
    if mission.get("icon"):
        content += f"\n## Icon\n{mission['icon']}\n"
    (topic_dir / "MISSION.md").write_text(content, encoding="utf-8")


def write_syllabus_file(topic_dir, syllabus):
    lines = [f"{i+1}. {title}" for i, title in enumerate(syllabus)]
    (topic_dir / "SYLLABUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def strip_code_fences(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    start = text.find("<!DOCTYPE html>")
    if start == -1:
        start = text.find("<!doctype html>")
    if start > 0:
        text = text[start:]
    end = text.rfind("</html>")
    if end != -1:
        text = text[:end + len("</html>")]
    return text
