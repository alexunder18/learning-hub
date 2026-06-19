import os
import secrets

from flask import Flask

from .config import load_config
from .security import generate_csrf_token


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
    )
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

    @app.context_processor
    def inject_globals():
        from flask import request, session
        cfg = load_config()
        return {
            "ui_lang": request.cookies.get("school_lang", "en"),
            "configured": cfg is not None,
            "school_name": cfg.get("school_name", "Home School") if cfg else "Home School",
            "csrf_token": generate_csrf_token,
        }

    from .routes import pages, api
    app.register_blueprint(pages.bp)
    app.register_blueprint(api.bp)

    return app
