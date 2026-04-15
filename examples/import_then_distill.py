from __future__ import annotations

import argparse
import json
from pathlib import Path

from aegisforge import AegisForge


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a log file and distill lessons.")
    parser.add_argument("--path", required=True, help="Path to JSONL or text log file")
    parser.add_argument("--root", default=".aegisforge", help="AegisForge data root")
    parser.add_argument(
        "--field-map",
        default="",
        help='Optional JSON field map, e.g. {"message":"msg","error_type":"level","source":"component"}',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    af = AegisForge(args.root)

    field_map = json.loads(args.field_map) if args.field_map else None
    import_result = af.import_log(Path(args.path), field_map=field_map)
    print("import result:")
    print(import_result)

    lessons = af.distill(max_lessons=5)
    print("distilled lessons:")
    for lesson in lessons:
        print(f"- {lesson.get('text', '')}")


if __name__ == "__main__":
    main()
