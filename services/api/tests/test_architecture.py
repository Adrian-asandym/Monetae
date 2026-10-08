import ast
from pathlib import Path

import pytest

DOMAIN_ROOT = Path(__file__).resolve().parents[1] / "src/monetae/domain"
FORBIDDEN = {"monetae.api", "monetae.db", "monetae.importers"}


def forbidden_imports(source: str, package: str) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(ast.parse(source)):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".")
                base = ".".join(parts[: len(parts) - node.level + 1]) + (f".{base}" if base else "")
            modules = [base, *(f"{base}.{alias.name}" for alias in node.names)]
        for module in modules:
            if any(module == prefix or module.startswith(f"{prefix}.") for prefix in FORBIDDEN):
                violations.append(module)
    return violations


def test_domain_does_not_import_outer_layers() -> None:
    for path in DOMAIN_ROOT.rglob("*.py"):
        relative = path.relative_to(DOMAIN_ROOT.parent).with_suffix("")
        parts = relative.parts if path.name == "__init__.py" else relative.parts[:-1]
        if path.name == "__init__.py":
            parts = parts[:-1]
        package = ".".join(("monetae", *parts))
        assert not forbidden_imports(path.read_text(), package), str(path)


@pytest.mark.parametrize(
    "source,package",
    [
        ("import monetae.api.main", "monetae.domain"),
        ("from monetae.db import models", "monetae.domain"),
        ("from monetae import importers", "monetae.domain"),
        ("from ..api import main", "monetae.domain"),
        ("from .. import db", "monetae.domain"),
        ("from ...db import models", "monetae.domain.nested"),
    ],
)
def test_architecture_guard_detects_forbidden_imports(source: str, package: str) -> None:
    assert forbidden_imports(source, package)


def test_architecture_guard_allows_domain_imports() -> None:
    assert not forbidden_imports(
        "from . import money\nfrom decimal import Decimal", "monetae.domain"
    )
