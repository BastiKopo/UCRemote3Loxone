"""Convenience wrapper to build the Remote 3 integration archive without installing."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    src_dir = project_root / "src"
    sys.path.insert(0, str(src_dir))

    from ucremote3loxone.packaging import build_integration_archive

    archive = build_integration_archive(root=project_root)
    print(f"Created integration archive at {archive}")


if __name__ == "__main__":
    main()
