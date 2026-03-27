"""Unit tests for failure-branch adaptation module.

Covers:
  1. Normal path — no failure detected
  2. Failure-branch trigger — each failure type
  3. Successful correction — retest passes
  4. Failed correction fallback — retest fails, original failure persists
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

# Ensure otto root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memory.failure_branch import (
    detect_failure,
    analyze_root_cause,
    validate_retest,
    DetectionResult,
    RootCauseAnalysis,
    RetestResult,
    _infer_category,
    _build_fallback_correction,
)


class TestDetectFailure(unittest.TestCase):
    """Test failure detection with pattern matching."""

    def test_normal_path_clean_output(self):
        """No failure detected on clean output with exit code 0."""
        result = detect_failure(
            task_output="Task completed successfully. All files written.",
            exit_code=0,
        )
        self.assertFalse(result.detected)
        self.assertIsNone(result.failure_type)
        self.assertEqual(result.confidence, 0.0)

    def test_normal_path_empty_output(self):
        """No failure on empty output with exit code 0."""
        result = detect_failure(task_output="", exit_code=0)
        self.assertFalse(result.detected)

    def test_error_traceback(self):
        """Detect Python traceback as error type."""
        output = """Traceback (most recent call last):
  File "test.py", line 5, in <module>
    raise ValueError("bad input")
ValueError: bad input"""
        result = detect_failure(task_output=output, exit_code=1)
        self.assertTrue(result.detected)
        self.assertEqual(result.failure_type, "error")
        self.assertGreaterEqual(result.confidence, 0.8)

    def test_error_nonzero_exit(self):
        """Detect non-zero exit code as error."""
        result = detect_failure(task_output="Some output", exit_code=1)
        self.assertTrue(result.detected)
        self.assertEqual(result.failure_type, "error")
        self.assertGreaterEqual(result.confidence, 0.8)

    def test_timeout_budget_exceeded(self):
        """Detect budget exceeded as timeout type."""
        output = "Error: budget exceeded after 25 turns. Task incomplete."
        result = detect_failure(task_output=output, exit_code=0)
        self.assertTrue(result.detected)
        self.assertEqual(result.failure_type, "timeout")
        self.assertGreaterEqual(result.confidence, 0.5)

    def test_timeout_oom(self):
        """Detect OOM as timeout type."""
        output = "Process killed by SIGKILL — out of memory"
        result = detect_failure(task_output=output, exit_code=137)
        self.assertTrue(result.detected)
        self.assertEqual(result.failure_type, "timeout")
        self.assertGreaterEqual(result.confidence, 0.8)

    def test_dependency_import_error(self):
        """Detect import error as dependency type."""
        output = "ModuleNotFoundError: No module named 'nonexistent_pkg'"
        result = detect_failure(task_output=output, exit_code=1)
        self.assertTrue(result.detected)
        self.assertEqual(result.failure_type, "dependency")
        self.assertGreaterEqual(result.confidence, 0.8)

    def test_dependency_connection_refused(self):
        """Detect connection refused as dependency type."""
        output = "requests.exceptions.ConnectionError: Connection refused to localhost:9999"
        result = detect_failure(task_output=output, exit_code=0)
        self.assertTrue(result.detected)
        self.assertEqual(result.failure_type, "dependency")

    def test_quality_test_failure(self):
        """Detect test failures as quality type."""
        output = "FAILED: 3 tests failed, 7 passed\nassert result == expected"
        result = detect_failure(task_output=output, exit_code=1)
        self.assertTrue(result.detected)
        # exit_code=1 gives error at 0.8, but test failure pattern gives quality at 0.75
        # error wins because 0.8 > 0.75 — but exit code comes first, then patterns override if higher
        # Actually: non-zero exit sets error@0.8, then patterns scan. "tests failed" is quality@0.75 which is < 0.8
        # So error wins. With exit_code=0, quality would win.
        # Let's test with exit_code=0
        result2 = detect_failure(task_output=output, exit_code=0)
        self.assertTrue(result2.detected)
        self.assertEqual(result2.failure_type, "quality")

    def test_approach_wrong_strategy(self):
        """Detect approach failure when agent is stuck."""
        output = "I'm unable to determine the correct approach. This approach doesn't work for the given constraints."
        result = detect_failure(task_output=output, exit_code=0)
        self.assertTrue(result.detected)
        self.assertEqual(result.failure_type, "approach")

    def test_retry_count_metadata(self):
        """Detect approach failure from high retry count in metadata."""
        result = detect_failure(
            task_output="Some bland output with no patterns",
            exit_code=0,
            task_metadata={"retry_count": 3},
        )
        self.assertTrue(result.detected)
        self.assertEqual(result.failure_type, "approach")
        self.assertGreaterEqual(result.confidence, 0.5)

    def test_below_threshold_not_detected(self):
        """Weak signals below 0.5 threshold should not trigger detection."""
        # Normal-looking output with no failure patterns
        result = detect_failure(
            task_output="Working on the implementation. Making progress.",
            exit_code=0,
        )
        self.assertFalse(result.detected)

    def test_highest_confidence_wins(self):
        """When multiple patterns match, highest confidence wins."""
        output = "Traceback (most recent call last):\n  File 'x.py'\nModuleNotFoundError: No module named 'foo'"
        result = detect_failure(task_output=output, exit_code=0)
        self.assertTrue(result.detected)
        # Traceback is error@0.9, ModuleNotFoundError is dependency@0.85
        # Traceback has higher confidence, but we iterate all patterns and take max
        self.assertEqual(result.failure_type, "error")
        self.assertGreaterEqual(result.confidence, 0.9)


class TestRootCauseAnalysis(unittest.TestCase):
    """Test LLM-powered root-cause analysis and correction."""

    def test_successful_correction_with_llm(self):
        """LLM returns valid analysis and correction."""
        mock_response = '{"root_cause": "Missing dependency", "category": "dependency", "correction_strategy": "Install the package first", "corrected_prompt_additions": "Before starting, run: pip install foo"}'

        async def run():
            with patch("memory.llm.llm_chat", new_callable=AsyncMock, return_value=mock_response):
                with patch("memory.llm.extract_json", return_value={
                    "root_cause": "Missing dependency",
                    "category": "dependency",
                    "correction_strategy": "Install the package first",
                    "corrected_prompt_additions": "Before starting, run: pip install foo",
                }):
                    result = await analyze_root_cause(
                        failure_type="dependency",
                        failure_signal="ModuleNotFoundError: No module named 'foo'",
                        original_prompt="Build feature X",
                        task_output="ModuleNotFoundError: No module named 'foo'",
                    )
                    return result

        result = asyncio.get_event_loop().run_until_complete(run())
        self.assertEqual(result.root_cause, "Missing dependency")
        self.assertEqual(result.category, "dependency")
        self.assertIn("FAILURE-BRANCH CORRECTION", result.corrected_prompt)
        self.assertIn("Build feature X", result.corrected_prompt)

    def test_fallback_when_llm_fails(self):
        """Falls back to pattern-based correction when LLM returns garbage."""
        async def run():
            with patch("memory.llm.llm_chat", new_callable=AsyncMock, return_value="not json"):
                with patch("memory.llm.extract_json", return_value=None):
                    result = await analyze_root_cause(
                        failure_type="error",
                        failure_signal="ValueError: bad input",
                        original_prompt="Run the task",
                        task_output="ValueError: bad input",
                    )
                    return result

        result = asyncio.get_event_loop().run_until_complete(run())
        self.assertIn("error failure", result.root_cause)
        self.assertEqual(result.category, "logic")  # error -> logic mapping
        self.assertIn("FAILURE-BRANCH CORRECTION", result.corrected_prompt)
        self.assertIn("Run the task", result.corrected_prompt)


class TestRetestValidation(unittest.TestCase):
    """Test retest harness validation."""

    def test_successful_retest(self):
        """Retest passes when caller reports success and no failure recurs."""
        result = validate_retest(
            retest_output="All checks passed. Feature works correctly.",
            retest_passed=True,
            original_failure_type="error",
        )
        self.assertTrue(result.passed)
        self.assertIn("resolved", result.details)

    def test_failed_retest_caller_reports_failure(self):
        """Retest fails when caller explicitly reports failure."""
        result = validate_retest(
            retest_output="Still broken",
            retest_passed=False,
            original_failure_type="error",
        )
        self.assertFalse(result.passed)
        self.assertIn("Retest reported failure", result.details)

    def test_failed_retest_same_failure_recurs(self):
        """Retest fails even if caller says pass but same failure type recurs."""
        result = validate_retest(
            retest_output="Traceback (most recent call last):\n  File 'test.py'\nValueError: same error again",
            retest_passed=True,
            original_failure_type="error",
        )
        self.assertFalse(result.passed)
        self.assertIn("still present", result.details)

    def test_different_failure_type_passes(self):
        """Retest passes if a different failure type appears (not the original)."""
        # Original was "dependency", new output has "error" pattern but not dependency
        result = validate_retest(
            retest_output="AssertionError: wrong value",
            retest_passed=True,
            original_failure_type="dependency",
        )
        # "AssertionError" doesn't match dependency patterns
        # The assertion_error pattern maps to "quality" not "dependency"
        # So this should pass since original_failure_type was "dependency"
        self.assertTrue(result.passed)


class TestHelpers(unittest.TestCase):
    """Test helper functions."""

    def test_infer_category_mapping(self):
        """Category inference maps all known failure types."""
        self.assertEqual(_infer_category("timeout"), "environment")
        self.assertEqual(_infer_category("error"), "logic")
        self.assertEqual(_infer_category("quality"), "prompt")
        self.assertEqual(_infer_category("approach"), "scope")
        self.assertEqual(_infer_category("dependency"), "dependency")
        self.assertEqual(_infer_category("unknown_type"), "unknown")

    def test_fallback_correction_includes_original(self):
        """Fallback correction preserves original prompt."""
        result = _build_fallback_correction(
            failure_type="error",
            failure_signal="ValueError occurred",
            original_prompt="Build the feature",
        )
        self.assertIn("FAILURE-BRANCH CORRECTION", result)
        self.assertIn("Build the feature", result)
        self.assertIn("ValueError occurred", result)

    def test_fallback_correction_truncates_signal(self):
        """Fallback correction truncates long signals."""
        long_signal = "x" * 500
        result = _build_fallback_correction(
            failure_type="error",
            failure_signal=long_signal,
            original_prompt="Do stuff",
        )
        # Signal should be truncated to 200 chars
        self.assertLessEqual(len(result.split("Previous attempt failed: ")[1].split("\n")[0]), 200)


if __name__ == "__main__":
    unittest.main()
