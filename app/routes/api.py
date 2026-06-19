import json
import re
import shutil
import time

from flask import Blueprint, request, jsonify, session

from ..config import load_config, save_config, get_topics_dir
from ..security import (
    require_auth_api, require_csrf, rate_limit,
    validate_api_base, hash_pin,
)
from ..providers import ai_chat, _cli_complete, _anthropic_complete, _openai_complete
from ..prompts import TEACH_SYSTEM_PROMPT
from ..topics import (
    slugify, write_mission_file, write_syllabus_file,
    load_syllabus, get_existing_lesson_numbers,
)
from ..generator import (
    queue_lesson, get_lesson_status, setup_new_topic,
    active_generation, lesson_queues,
)

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/setup", methods=["POST"])
def setup():
    data = request.json

    api_base = data.get("api_base", "")
    if not validate_api_base(api_base):
        return jsonify({"error": "Invalid API base URL. Only known provider URLs and localhost are allowed."}), 400

    cfg = {
        "school_name": data.get("school_name", "Home School"),
        "mode": data.get("mode", "api"),
        "provider": data.get("provider", "anthropic"),
        "model": data.get("model", ""),
        "api_key": data.get("api_key", ""),
        "api_base": api_base,
        "initial_lessons": data.get("initial_lessons", 3),
        "topics_dir": data.get("topics_dir", "./topics"),
    }

    pin = data.get("pin", "")
    if pin:
        cfg["pin_hash"] = hash_pin(pin)
        session["authenticated"] = True
        session["last_active"] = time.time()

    save_config(cfg)
    return jsonify({"ok": True})


@bp.route("/test-connection", methods=["POST"])
@rate_limit(max_requests=5, window=60)
def test_connection():
    data = request.json
    mode = data.get("mode", "api")
    provider = data.get("provider", "anthropic")
    model = data.get("model", "")
    api_key = data.get("api_key", "")
    api_base = data.get("api_base", "")

    if not validate_api_base(api_base):
        return jsonify({"ok": False, "error": "Invalid API base URL. Only known provider URLs and localhost are allowed."})

    try:
        test_prompt = "Reply with exactly: OK"
        if mode == "cli":
            result = _cli_complete(test_prompt, model, timeout=30)
        elif provider == "anthropic":
            result = _anthropic_complete(test_prompt, model, api_key, timeout=30)
        elif provider in ("openai", "ollama"):
            if provider == "ollama" and not api_base:
                api_base = "http://localhost:11434"
            result = _openai_complete(test_prompt, model, api_key, api_base, timeout=30)
        else:
            return jsonify({"ok": False, "error": f"Unknown provider: {provider}"})
        return jsonify({"ok": True, "response": result[:100]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@bp.route("/chat", methods=["POST"])
@require_auth_api
@require_csrf
@rate_limit(max_requests=20, window=60)
def chat():
    data = request.json
    messages = data.get("messages", [])

    try:
        reply = ai_chat(messages, TEACH_SYSTEM_PROMPT)

        mission_match = re.search(r"<mission>\s*(\{.*?\})\s*</mission>", reply, re.DOTALL)
        if mission_match:
            try:
                mission = json.loads(mission_match.group(1))
                display_text = re.sub(r"<mission>.*?</mission>", "", reply, flags=re.DOTALL).strip()
                return jsonify({
                    "message": reply,
                    "html": display_text.replace("\n", "<br>") if display_text else "",
                    "mission_ready": True,
                    "mission": mission,
                })
            except json.JSONDecodeError:
                pass

        options = []
        options_match = re.search(r"<options>\s*(\[.*?\])\s*</options>", reply, re.DOTALL)
        if options_match:
            try:
                options = json.loads(options_match.group(1))
            except json.JSONDecodeError:
                pass
            display_reply = re.sub(r"<options>.*?</options>", "", reply, flags=re.DOTALL).strip()
        else:
            display_reply = reply

        html = f"<p>{display_reply.replace(chr(10)*2, '</p><p>').replace(chr(10), '<br>')}</p>"

        return jsonify({
            "message": reply,
            "html": html,
            "mission_ready": False,
            "options": options,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/approve-topic", methods=["POST"])
@require_auth_api
@require_csrf
def approve_topic():
    data = request.json
    mission = data.get("mission")
    if not mission:
        return jsonify({"error": "No mission data"}), 400

    slug = mission.get("slug") or slugify(mission.get("topic_name", "untitled"))
    topics_dir = get_topics_dir()
    topic_dir = topics_dir / slug

    if topic_dir.exists():
        return jsonify({"error": f"Topic '{slug}' already exists"}), 400

    topic_dir.mkdir(parents=True, exist_ok=True)
    for subdir in ("lessons", "reference", "learning-records"):
        (topic_dir / subdir).mkdir(exist_ok=True)

    write_mission_file(topic_dir, mission)
    write_syllabus_file(topic_dir, mission.get("syllabus", []))
    setup_new_topic(slug, mission)

    return jsonify({"ok": True, "slug": slug})


@bp.route("/generate-lesson/<slug>/<int:num>", methods=["POST"])
@require_auth_api
@require_csrf
@rate_limit(max_requests=10, window=60)
def generate_lesson(slug, num):
    topics_dir = get_topics_dir()
    topic_dir = topics_dir / slug
    if not topic_dir.is_dir():
        return jsonify({"error": "Topic not found"}), 404

    existing = get_existing_lesson_numbers(topic_dir / "lessons")
    if num in existing:
        return jsonify({"error": "Lesson already exists"}), 409

    status = get_lesson_status(slug, num)
    if status in ("generating", "queued"):
        return jsonify({"error": "Already in queue"}), 409

    return jsonify({"ok": queue_lesson(slug, num)})


@bp.route("/topic-status/<slug>")
@require_auth_api
def topic_status(slug):
    topics_dir = get_topics_dir()
    topic_dir = topics_dir / slug
    if not topic_dir.is_dir():
        return jsonify({"error": "Topic not found"}), 404

    syllabus = load_syllabus(topic_dir)
    lessons = {str(i): get_lesson_status(slug, i) for i in range(1, len(syllabus) + 1)}
    any_active = slug in active_generation or (slug in lesson_queues and len(lesson_queues[slug]) > 0)

    return jsonify({"lessons": lessons, "any_active": any_active})


@bp.route("/status")
@require_auth_api
def status():
    any_generating = bool(active_generation) or any(len(q) > 0 for q in lesson_queues.values())
    return jsonify({"any_generating": any_generating})


@bp.route("/delete-topic/<slug>", methods=["DELETE"])
@require_auth_api
@require_csrf
def delete_topic(slug):
    topics_dir = get_topics_dir()
    topic_dir = topics_dir / slug
    if not topic_dir.is_dir():
        return jsonify({"error": "Topic not found"}), 404

    if slug in active_generation:
        return jsonify({"error": "Cannot delete while generating"}), 409

    from ..generator import queue_lock
    with queue_lock:
        lesson_queues.pop(slug, None)

    shutil.rmtree(topic_dir)
    return jsonify({"ok": True})
