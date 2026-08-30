from datetime import timezone
import unittest

from promise_pocket.arbiter_v2 import ARBITER_PROMPT, _parse_optional_datetime


class ArbiterV2Tests(unittest.TestCase):
    def test_prompt_keeps_model_in_candidate_role(self):
        prompt = ARBITER_PROMPT.casefold()

        self.assertIn("candidate", prompt)
        self.assertIn("never user confirmation", prompt)
        self.assertIn("never invent a deadline", prompt)

    def test_due_at_requires_offset(self):
        with self.assertRaises(ValueError):
            _parse_optional_datetime("2026-09-01T18:00:00")

    def test_due_at_with_offset_is_accepted(self):
        parsed = _parse_optional_datetime("2026-09-01T18:00:00-04:00")

        self.assertIsNotNone(parsed.tzinfo)
        self.assertEqual(-4 * 60 * 60, parsed.utcoffset().total_seconds())

    def test_null_due_at_is_allowed(self):
        self.assertIsNone(_parse_optional_datetime(None))


if __name__ == "__main__":
    unittest.main()
