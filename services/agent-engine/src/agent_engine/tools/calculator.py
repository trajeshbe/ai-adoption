"""Safe math expression evaluator.

Uses the AST module to parse and evaluate arithmetic expressions without
executing arbitrary code (no eval/exec).
"""

from __future__ import annotations

import ast
import operator
from typing import Any

# Allowed binary and unary operators
_OPERATORS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float | int:
    """Recursively evaluate an AST node containing only arithmetic."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op = _OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return op(left, right)
    if isinstance(node, ast.UnaryOp):
        op = _OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def calculate(expression: str) -> dict:
    """Evaluate a math expression safely.

    Returns:
        dict with keys: expression, result, error.
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree)
        return {"expression": expression, "result": result, "error": None}
    except Exception as exc:
        return {"expression": expression, "result": None, "error": str(exc)}
