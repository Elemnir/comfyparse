import unittest

from comfyparse.parser import ComfyParser


simple_valid_text = """
group servers {
    hosts = [ # end of line comments should work
        "node01", "node02'"
    ] % multiple flavors too
    timeout = 30.0f
}
log_path=/var/log/my.log
"""


class TestParser(unittest.TestCase):
    def test_adding_settings(self):
        parser = ComfyParser()
        parser.add_setting("log_path")

        config = parser.parse_config_string("log_path=/var/log/my.log")
        self.assertEqual(config.log_path, "/var/log/my.log")
