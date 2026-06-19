import threading
import traceback
from collections import deque

from .config import load_config, get_topics_dir, DEFAULT_CONFIG
from .providers import ai_generate
from .prompts import LESSON_SYSTEM_PROMPT
from .security import sanitize_lesson_html

lesson_queues = {}
active_generation = {}
queue_lock = threading.Lock()


def is_generating(slug):
    return slug in active_generation or slug in lesson_queues


def get_lesson_status(slug, lesson_num):
    from .topics import get_existing_lesson_numbers
    topics_dir = get_topics_dir()
    lessons_dir = topics_dir / slug / "lessons"
    existing = get_existing_lesson_numbers(lessons_dir)

    if lesson_num in existing:
        return "completed"
    with queue_lock:
        active = active_generation.get(slug)
        if active == lesson_num:
            return "generating"
        if active is None and slug in active_generation:
            if slug in lesson_queues and lesson_queues[slug] and lesson_queues[slug][0] == lesson_num:
                return "generating"
        if slug in lesson_queues and lesson_num in lesson_queues[slug]:
            return "queued"
    return "available"


def queue_lesson(slug, lesson_num):
    from .topics import get_existing_lesson_numbers

    with queue_lock:
        if slug not in lesson_queues:
            lesson_queues[slug] = deque()
        if lesson_num in lesson_queues[slug]:
            return False
        if active_generation.get(slug) == lesson_num:
            return False

        topics_dir = get_topics_dir()
        existing = get_existing_lesson_numbers(topics_dir / slug / "lessons")
        if lesson_num in existing:
            return False

        lesson_queues[slug].append(lesson_num)

        if slug not in active_generation:
            active_generation[slug] = None
            threading.Thread(target=_queue_worker, args=(slug,), daemon=True).start()

    return True


def _queue_worker(slug):
    while True:
        with queue_lock:
            if slug not in lesson_queues or not lesson_queues[slug]:
                lesson_queues.pop(slug, None)
                active_generation.pop(slug, None)
                return
            lesson_num = lesson_queues[slug].popleft()
            active_generation[slug] = lesson_num

        try:
            _generate_single_lesson(slug, lesson_num)
            print(f"[DONE] {slug}: lesson {lesson_num} generated")
        except Exception as e:
            print(f"[ERROR] {slug}: lesson {lesson_num} failed: {e}")
            traceback.print_exc()

        with queue_lock:
            active_generation.pop(slug, None)


def _generate_single_lesson(slug, lesson_num):
    from .topics import parse_mission_file, load_syllabus, slugify, strip_code_fences

    topics_dir = get_topics_dir()
    topic_dir = topics_dir / slug
    lessons_dir = topic_dir / "lessons"
    lessons_dir.mkdir(exist_ok=True)

    mission = parse_mission_file(topic_dir / "MISSION.md")
    syllabus = load_syllabus(topic_dir)
    language = mission.get("language", "en")
    lesson_title = syllabus[lesson_num - 1] if lesson_num <= len(syllabus) else f"Lesson {lesson_num}"

    print(f"[GENERATING] {slug}: lesson {lesson_num} — {lesson_title}")

    existing = sorted(lessons_dir.glob("*.html"))
    existing_list = "\n".join(f"- {f.name}" for f in existing) or "None"

    next_title = syllabus[lesson_num] if syllabus and lesson_num < len(syllabus) else "To be determined"
    last_content = existing[-1].read_text(encoding="utf-8")[:2000] if existing else ""
    syllabus_text = "\n".join(f"{j+1}. {t}" for j, t in enumerate(syllabus)) if syllabus else "No syllabus defined"

    prompt = f"""Create lesson {lesson_num}: "{lesson_title}"

Mission: {mission.get('why', 'Not specified')}
Topic: {mission.get('name', slug.replace('-', ' ').title())}
Slug: {slug}
Language: {language}

Full syllabus:
{syllabus_text}

Previous lessons created:
{existing_list}

Summary of last lesson (for continuity):
{last_content or 'N/A'}

Next lesson number: {lesson_num + 1}
Next lesson title: "{next_title}"
This is the last lesson: {"yes" if lesson_num >= len(syllabus) else "no"}

Prior knowledge: {mission.get('prior_knowledge', 'None specified')}
Out of scope: {', '.join(mission.get('out_of_scope', ['None specified'])) if isinstance(mission.get('out_of_scope'), list) else 'None specified'}

Generate the complete HTML lesson now."""

    html = ai_generate(prompt, LESSON_SYSTEM_PROMPT)
    html = sanitize_lesson_html(strip_code_fences(html))

    filename = f"{lesson_num:04d}-{slugify(lesson_title)}.html"
    (lessons_dir / filename).write_text(html, encoding="utf-8")
    print(f"[SAVED] {slug}: {filename}")


def _generate_glossary(slug, mission):
    from .topics import strip_code_fences

    topics_dir = get_topics_dir()
    reference_dir = topics_dir / slug / "reference"
    reference_dir.mkdir(exist_ok=True)

    syllabus = mission.get("syllabus", [])
    language = mission.get("language", "en")
    covered = syllabus[:3] if len(syllabus) >= 3 else syllabus

    print(f"[GENERATING] {slug}: glossary")

    prompt = f"""Create a glossary reference document for the topic "{mission['topic_name']}".
Language: {language}

Based on lessons covering:
{chr(10).join(f'- {t}' for t in covered)}

Create a beautiful, self-contained HTML reference document with:
- Clean Tufte-inspired styling (same CSS variables as the lessons)
- All key terms defined concisely
- Organized logically

Output ONLY the complete HTML. Start with <!DOCTYPE html>."""

    html = ai_generate(prompt, LESSON_SYSTEM_PROMPT)
    html = sanitize_lesson_html(strip_code_fences(html))
    (reference_dir / "glossary.html").write_text(html, encoding="utf-8")
    print(f"[SAVED] {slug}: glossary")


def setup_new_topic(slug, mission):
    cfg = load_config() or DEFAULT_CONFIG
    initial_count = cfg.get("initial_lessons", 3)
    syllabus_len = len(mission.get("syllabus", []))
    for i in range(1, min(initial_count + 1, syllabus_len + 1)):
        queue_lesson(slug, i)

    threading.Thread(target=_generate_glossary, args=(slug, mission), daemon=True).start()
