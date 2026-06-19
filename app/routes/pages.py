import re
import time

from flask import Blueprint, render_template, request, redirect, session, send_from_directory, abort

from ..config import load_config, get_topics_dir
from ..security import require_auth, verify_pin
from ..topics import get_topics, get_topic_detail, parse_mission_file, load_syllabus
from ..generator import get_lesson_status

bp = Blueprint("pages", __name__)


@bp.route("/")
@require_auth
def index():
    topics = get_topics()
    return render_template(
        "index.html",
        topics=topics,
        total_lessons=sum(t["lesson_count"] for t in topics),
        total_refs=sum(t["reference_count"] for t in topics),
        any_generating=any(t["is_generating"] for t in topics),
    )


@bp.route("/setup")
def setup_page():
    cfg = load_config()
    if cfg and cfg.get("pin_hash") and not session.get("authenticated"):
        return redirect("/login")
    return render_template("setup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    cfg = load_config()
    if not cfg or not cfg.get("pin_hash"):
        return redirect("/")
    if request.method == "POST":
        pin = request.form.get("pin", "")
        if verify_pin(pin, cfg["pin_hash"]):
            session["authenticated"] = True
            session["last_active"] = time.time()
            return redirect("/")
        return render_template("login.html", error=True)
    return render_template("login.html", error=False)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@bp.route("/topic/<slug>")
@require_auth
def topic_page(slug):
    topic = get_topic_detail(slug)
    if not topic:
        abort(404)
    return render_template("topic.html", topic=topic)


@bp.route("/topic/<slug>/lesson/<int:num>")
@require_auth
def serve_lesson_by_num(slug, num):
    topics_dir = get_topics_dir()
    topic_dir = topics_dir / slug
    lessons_dir = topic_dir / "lessons"
    if lessons_dir.exists():
        for f in lessons_dir.glob(f"{num:04d}-*.html"):
            return send_from_directory(str(lessons_dir), f.name)
    mission = parse_mission_file(topic_dir / "MISSION.md")
    syllabus = load_syllabus(topic_dir)
    language = mission.get("language", "en")
    title = syllabus[num - 1] if num <= len(syllabus) else f"Lesson {num}"
    status = get_lesson_status(slug, num)
    return render_template("lesson_pending.html", slug=slug, lesson_num=num,
                           title=title, status=status, language=language)


@bp.route("/topic/<slug>/lessons/<path:filename>")
@require_auth
def serve_lesson(slug, filename):
    topics_dir = get_topics_dir()
    topic_dir = topics_dir / slug
    lessons_dir = topic_dir / "lessons"
    if (lessons_dir / filename).exists():
        return send_from_directory(str(lessons_dir), filename)

    num_match = re.match(r"(\d+)", filename)
    if num_match:
        lesson_num = int(num_match.group(1))
        mission = parse_mission_file(topic_dir / "MISSION.md")
        syllabus = load_syllabus(topic_dir)
        language = mission.get("language", "en")
        title = syllabus[lesson_num - 1] if lesson_num <= len(syllabus) else f"Lesson {lesson_num}"
        status = get_lesson_status(slug, lesson_num)
        return render_template("lesson_pending.html", slug=slug, lesson_num=lesson_num,
                               title=title, status=status, language=language)
    abort(404)


@bp.route("/topic/<slug>/reference/<path:filename>")
@require_auth
def serve_reference(slug, filename):
    topics_dir = get_topics_dir()
    ref_dir = topics_dir / slug / "reference"
    if not (ref_dir / filename).exists():
        abort(404)
    return send_from_directory(str(ref_dir), filename)


@bp.route("/new-topic")
@require_auth
def new_topic():
    return render_template("chat.html")


@bp.route("/new-topic/confirm")
@require_auth
def confirm_topic():
    return render_template("confirm.html")
