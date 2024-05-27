import unittest

from comfyparse.parser import ComfyParser
from comfyparse.config import ConfigSpecError, ValidationError

simple_valid_text = """
group servers {
    hosts = [ # end of line comments should work
        "node01", "node02'"
    ] % multiple flavors too
    timeout = 30.0f
}
log_path=/var/log/my.log
"""


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.parser = ComfyParser()
        self.parser.add_setting("log_path", required=True)
        self.parser.add_setting("log_level", default=5, convert=int)

    def test_default_value(self):
        config = self.parser.parse_config_string("log_path=/var/log/my.log;")
        self.assertEqual(config.log_path, "/var/log/my.log")
        self.assertEqual(config.log_level, 5)

    def test_override_default(self):
        config = self.parser.parse_config_string("log_path=/var/log/my.log\n log_level = 8;")
        self.assertEqual(config.log_path, "/var/log/my.log")
        self.assertEqual(config.log_level, 8)

    def test_adding_duplicate_setting(self):
        with self.assertRaises(ConfigSpecError):
            self.parser.add_setting("log_path")

    def test_missing_required_setting(self):
        with self.assertRaises(ValidationError):
            self.parser.parse_config_string("")

    def test_conversion_failure(self):
        with self.assertRaises(ValidationError):
            self.parser.parse_config_string("log_path=/var/log/my.log\n log_level = 'foo';")

class TestBlocks(unittest.TestCase):
    def setUp(self):
        self.parser = ComfyParser()
        block = self.parser.add_block("hostgroup")
        block.add_setting("hosts"
