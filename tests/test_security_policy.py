"""Security invariants for the deliberately small Mini Kanban application.

These checks are an automated guardrail for changes submitted by untrusted
contributors. Any expansion of this allow-list requires a maintainer-owned
security-policy change, rather than an application-only PR.
"""

import ast
from pathlib import Path

from app import create_app


APPLICATION_SOURCE = Path("app.py")
APPROVED_ROUTES = {
    "/",
    "/cards",
    "/cards/<int:card_id>/move",
    "/health",
    "/static/<path:filename>",
}
FORBIDDEN_IMPORT_ROOTS = {
    "asyncio",
    "ftplib",
    "http",
    "multiprocessing",
    "os",
    "pathlib",
    "pickle",
    "shutil",
    "socket",
    "subprocess",
    "urllib",
}
FORBIDDEN_CALLS = {"compile", "eval", "exec", "__import__", "open", "print"}


def _application_tree() -> ast.Module:
    return ast.parse(APPLICATION_SOURCE.read_text(encoding="utf-8"))


def test_application_exposes_only_approved_http_routes():
    app = create_app("sqlite:///:memory:")
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert routes == APPROVED_ROUTES


def test_application_does_not_import_network_process_or_host_access_modules():
    forbidden_imports = []
    for node in ast.walk(_application_tree()):
        if isinstance(node, ast.Import):
            forbidden_imports.extend(alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            forbidden_imports.append(node.module.split(".")[0])

    assert not (set(forbidden_imports) & FORBIDDEN_IMPORT_ROOTS)


def test_application_has_no_dynamic_execution_file_access_or_debug_prints():
    forbidden_calls = []
    for node in ast.walk(_application_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                forbidden_calls.append(node.func.id)

    assert not forbidden_calls
