import unittest

from promise_pocket.arbiter_v2 import ARBITER_PROMPT


class ArbiterV2Tests(unittest.TestCase):
    def test_prompt_keeps_model_in_candidate_role(self):
        prompt = ARBITER_PROMPT.casefold()

        self.assertIn("candidate", prompt)
        self.assertIn("never user confirmation", prompt)
        self.assertIn("time_phrase", prompt)
        self.assertIn("do not calculate", prompt)

    def test_prompt_rejects_generic_people_labels(self):
        prompt = ARBITER_PROMPT.casefold()

        self.assertIn("generic labels", prompt)
        self.assertIn("recipient", prompt)
        self.assertIn("sender", prompt)


if __name__ == "__main__":
    unittest.main()
