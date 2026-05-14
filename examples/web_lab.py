from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local Phone Mem Python Web Lab.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--delete-user", metavar="USERNAME", help="Delete a user's data and exit.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.delete_user:
        from phone_mem.web_lab.users import UserLabStateManager

        manager = UserLabStateManager()
        ok = manager.delete_user(args.delete_user)
        if ok:
            print(f"Deleted user '{args.delete_user}' and all associated data.")
        else:
            print(f"User '{args.delete_user}' not found or could not be deleted.")
        return

    import uvicorn

    uvicorn.run(
        "phone_mem.web_lab.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
