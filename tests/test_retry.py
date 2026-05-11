"""
test_retry.py
-------------
Unit tests for glacier_snow_analysis.retry.
"""

import pytest
from unittest.mock import MagicMock

from glacier_snow_analysis.retry import retry


class TestRetry:
    def test_succeeds_on_first_try(self):
        mock = MagicMock(return_value="ok")
        decorated = retry(max_attempts=3, delay=0)(mock)
        result = decorated()
        assert result == "ok"
        assert mock.call_count == 1

    def test_retries_on_failure_then_succeeds(self):
        call_count = {"n": 0}

        @retry(max_attempts=3, delay=0)
        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ConnectionError("transient")
            return "success"

        assert flaky() == "success"
        assert call_count["n"] == 3

    def test_raises_after_max_attempts(self):
        @retry(max_attempts=2, delay=0)
        def always_fails():
            raise RuntimeError("permanent failure")

        with pytest.raises(RuntimeError, match="permanent failure"):
            always_fails()

    def test_only_retries_specified_exceptions(self):
        call_count = {"n": 0}

        @retry(max_attempts=3, delay=0, exceptions=(ValueError,))
        def wrong_exception():
            call_count["n"] += 1
            raise TypeError("not in exceptions tuple")

        with pytest.raises(TypeError):
            wrong_exception()

        # Should NOT retry — TypeError is not in the tuple
        assert call_count["n"] == 1

    def test_preserves_function_name(self):
        @retry(max_attempts=1, delay=0)
        def my_function():
            pass

        assert my_function.__name__ == "my_function"
