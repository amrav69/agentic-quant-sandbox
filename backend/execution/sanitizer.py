"""AST-based code sanitizer for the sandboxed execution layer.

Validates generated strategy code BEFORE any subprocess is spawned.
Returns (True, None) when safe or (False, reason) when a violation is found.
"""

from __future__ import annotations

import ast
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Deny-lists
# ---------------------------------------------------------------------------

_BLOCKED_IMPORTS: frozenset[str] = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "requests",
        "httpx",
        "urllib",
        "shutil",
        "pathlib",
        "glob",
        "pickle",
        "shelve",
        "sqlite3",
        "threading",
        "multiprocessing",
        "ctypes",
        "importlib",
        "inspect",
    }
)

_BLOCKED_CALLS: frozenset[str] = frozenset(
    {
        "eval",
        "exec",
        "open",
        "__import__",
        "compile",
        "__subscript_call__",
        "breakpoint",
        "set_trace",
    }
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sanitize_code(code: str) -> tuple[bool, str | None]:
    """Validate *code* against the execution allow-list using AST analysis.

    Parameters
    ----------
    code : str
        Raw Python source code to inspect.

    Returns
    -------
    (is_safe, violation_reason)
        ``(True, None)``  — code passed all checks.
        ``(False, reason)`` — code was rejected; *reason* is a human-readable
        explanation.
    """
    # ── 1. Parse ──────────────────────────────────────────────────────────
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"SyntaxError during parse: {exc}"

    # ── 2. Walk AST ───────────────────────────────────────────────────────
    for node in ast.walk(tree):
        # ── 2a. Import statements (import X, import X as Y) ───────────────
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Match on the top-level package name
                top = alias.name.split(".")[0]
                if top in _BLOCKED_IMPORTS:
                    return False, f"Blocked import detected: '{alias.name}'"

        # ── 2b. From-import statements (from X import Y) ──────────────────
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top = module.split(".")[0]
            if top in _BLOCKED_IMPORTS:
                return False, f"Blocked import detected: 'from {module} import ...'"

        # ── 2c. Function calls (eval, exec, open, __import__, compile) ────
        elif isinstance(node, ast.Call):
            func_name = _extract_func_name(node.func)
            if func_name in _BLOCKED_CALLS:
                return False, f"Blocked function call detected: '{func_name}()'"

    logger.debug("sanitize_code: passed all checks")
    return True, None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_func_name(func_node: ast.expr) -> str:
    """Return the bare name of a callable node, or '' if not resolvable."""
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute):
        return func_node.attr
    if isinstance(func_node, ast.Subscript):
        # Block any subscript call such as:
        # __builtins__['exec'](...)
        return "__subscript_call__"
    return ""
