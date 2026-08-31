import os
import unittest
from unittest.mock import patch

from promise_pocket.settings import DEFAULT_MODEL_ID, Settings


SONNET_4_6_MODEL_ID = "us.anthropic.claude-sonnet-4-6"


class SettingsTests(unittest.TestCase):
    def test_sonnet_4_6_is_the_runtime_default(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_environment()

        self.assertEqual(SONNET_4_6_MODEL_ID, DEFAULT_MODEL_ID)
        self.assertEqual(SONNET_4_6_MODEL_ID, settings.model_id)

    def test_model_id_can_still_be_overridden(self):
        with patch.dict(os.environ, {"MODEL_ID": "test-model"}, clear=True):
            settings = Settings.from_environment()

        self.assertEqual("test-model", settings.model_id)


if __name__ == "__main__":
    unittest.main()
