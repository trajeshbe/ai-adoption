"""Tests for the safe math expression evaluator."""

from __future__ import annotations

import pytest

from agent_engine.tools.calculator import calculate


class TestCalculateBasicOps:
    """Test basic arithmetic operations."""

    def test_addition(self) -> None:
        result = calculate("2 + 3")
        assert result["result"] == 5
        assert result["error"] is None

    def test_subtraction(self) -> None:
        result = calculate("10 - 4")
        assert result["result"] == 6
        assert result["error"] is None

    def test_multiplication(self) -> None:
        result = calculate("6 * 7")
        assert result["result"] == 42
        assert result["error"] is None

    def test_division(self) -> None:
        result = calculate("15 / 4")
        assert result["result"] == 3.75
        assert result["error"] is None

    def test_floor_division(self) -> None:
        result = calculate("15 // 4")
        assert result["result"] == 3
        assert result["error"] is None

    def test_modulo(self) -> None:
        result = calculate("17 % 5")
        assert result["result"] == 2
        assert result["error"] is None

    def test_power(self) -> None:
        result = calculate("2 ** 10")
        assert result["result"] == 1024
        assert result["error"] is None

    def test_unary_negative(self) -> None:
        result = calculate("-5 + 3")
        assert result["result"] == -2
        assert result["error"] is None

    def test_unary_positive(self) -> None:
        result = calculate("+5")
        assert result["result"] == 5
        assert result["error"] is None


class TestCalculateComplexExpressions:
    """Test complex and nested expressions."""

    def test_nested_parentheses(self) -> None:
        result = calculate("(2 + 3) * (4 - 1)")
        assert result["result"] == 15
        assert result["error"] is None

    def test_mixed_operations(self) -> None:
        result = calculate("2 + 3 * 4")
        assert result["result"] == 14  # operator precedence
        assert result["error"] is None

    def test_floating_point(self) -> None:
        result = calculate("3.14 * 2")
        assert result["result"] == pytest.approx(6.28)
        assert result["error"] is None

    def test_expression_preserved(self) -> None:
        result = calculate("1 + 1")
        assert result["expression"] == "1 + 1"

    def test_whitespace_stripped(self) -> None:
        result = calculate("  42  ")
        assert result["result"] == 42
        assert result["error"] is None


class TestCalculateInvalidInputs:
    """Test invalid and dangerous inputs are rejected."""

    def test_function_call_rejected(self) -> None:
        result = calculate("__import__('os').system('ls')")
        assert result["result"] is None
        assert result["error"] is not None

    def test_variable_name_rejected(self) -> None:
        result = calculate("x + 1")
        assert result["result"] is None
        assert result["error"] is not None

    def test_string_literal_rejected(self) -> None:
        result = calculate("'hello'")
        assert result["result"] is None
        assert result["error"] is not None

    def test_empty_expression(self) -> None:
        result = calculate("")
        assert result["result"] is None
        assert result["error"] is not None

    def test_division_by_zero(self) -> None:
        result = calculate("1 / 0")
        assert result["result"] is None
        assert result["error"] is not None

    def test_list_comprehension_rejected(self) -> None:
        result = calculate("[x for x in range(10)]")
        assert result["result"] is None
        assert result["error"] is not None
