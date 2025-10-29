"""Helpers to assemble an integration archive for the Remote 3."""
from __future__ import annotations

import tarfile
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator


DEFAULT_ARCHIVE_NAME = "uc-remote3-loxone.tar.gz"


def build_integration_archive(
    output_dir: str | Path | None = None,
    *,
    root: str | Path | None = None,
    include_tests: bool = False,
) -> Path:
    """Create a tar.gz archive containing the driver ready for upload."""

    project_root = Path(root or _default_project_root()).resolve()
    destination_dir = Path(output_dir or project_root / "dist").resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)

    archive_path = destination_dir / DEFAULT_ARCHIVE_NAME
    files_to_package = list(_iter_integration_files(project_root, include_tests=include_tests))

    with tarfile.open(archive_path, "w:gz") as tar:
        for entry in files_to_package:
            tar.add(entry.source, arcname=str(entry.arcname))

    return archive_path


@dataclass(frozen=True)
class ArchiveEntry:
    source: Path
    arcname: Path


def _iter_integration_files(
    root: Path, *, include_tests: bool = False
) -> Iterator[ArchiveEntry]:
    yield ArchiveEntry(root / "pyproject.toml", Path("pyproject.toml"))

    integration_manifest = root / "integration.json"
    if integration_manifest.exists():
        yield ArchiveEntry(integration_manifest, Path("integration.json"))

    readme = root / "readme.md"
    if readme.exists():
        yield ArchiveEntry(readme, Path("readme.md"))

    package_dir = root / "src" / "ucremote3loxone"
    for path in sorted(package_dir.rglob("*")):
        if path.is_file() and _should_include_package_file(path):
            arcname = Path("ucremote3loxone") / path.relative_to(package_dir)
            yield ArchiveEntry(path, arcname)

    if include_tests:
        tests_dir = root / "tests"
        for path in sorted(tests_dir.rglob("*")):
            if path.is_file():
                arcname = Path("tests") / path.relative_to(tests_dir)
                yield ArchiveEntry(path, arcname)


def _should_include_package_file(path: Path) -> bool:
    """Return ``True`` when ``path`` should be bundled in the archive."""

    # ``tarfile`` happily packages bytecode caches which provide no value for
    # Remote 3 integrations and trigger an error in the upload UI.  Filter them
    # out so the archive only contains the actual source tree.
    if path.suffix == ".pyc":
        return False

    return "__pycache__" not in path.parts


def _default_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


__all__ = ["build_integration_archive", "DEFAULT_ARCHIVE_NAME"]


def _main() -> None:  # pragma: no cover - thin CLI wrapper
    archive = build_integration_archive()
    print(f"Created integration archive at {archive}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    _main()
