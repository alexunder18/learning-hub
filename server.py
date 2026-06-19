import argparse

from app import create_app
from app.config import load_config

app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Home School Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    name = cfg.get("school_name", "Home School") if cfg else "Home School"
    print(f"\n  {name}")
    print(f"  http://localhost:{args.port}")
    print(f"  http://0.0.0.0:{args.port} (network)\n")

    app.run(host=args.host, port=args.port, debug=args.debug)
