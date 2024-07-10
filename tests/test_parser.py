import datetime
import glob
import logging
import os
import shutil
import sys
import unittest

from comfyparse.parser import ComfyParser, ParseError
from comfyparse.config import ConfigSpecError, ValidationError, Namespace

logger = logging.getLogger("comfyparse")
#logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

simple_valid_text = """
group servers {
    hosts = [ # end of line comments should work
        "node01", "node02'"
    ] % multiple flavors too
    timeout = 30.0
}
log_path=/var/log/my.log
"""


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.parser = ComfyParser()
        self.parser.add_setting("log_path", required=True)
        self.parser.add_setting("log_level", default=5, convert=int, validate=lambda x: abs(x) == x)

    def test_default_value(self):
        config = self.parser.parse_config_string("log_path=/var/log/my.log;")
        self.assertEqual(config.log_path, "/var/log/my.log")
        self.assertEqual(config.log_level, 5)

    def test_newline_as_value(self):
        config = self.parser.parse_config_string("log_path='\\n'\n")
        self.assertEqual(config.log_path, "\n")

    def test_override_default(self):
        config = self.parser.parse_config_string("log_path=/var/log/my.log\n log_level = 8;")
        self.assertEqual(config.log_path, "/var/log/my.log")
        self.assertEqual(config.log_level, 8)

    def test_adding_duplicate_setting(self):
        with self.assertRaises(ConfigSpecError):
            self.parser.add_setting("log_path")

    def test_conflicting_options(self):
        with self.assertRaises(ConfigSpecError):
            self.parser.add_setting("conflict", required=True, default="foo")

    def test_missing_required_setting(self):
        with self.assertRaises(ValidationError):
            self.parser.parse_config_string("")

    def test_conversion_failure(self):
        with self.assertRaises(ValidationError):
            self.parser.parse_config_string("log_path=/var/log/my.log\n log_level = 'foo';")

    def test_validation_failure(self):
        with self.assertRaises(ValidationError):
            self.parser.parse_config_string("log_path=/var/log/my.log\n log_level = -5;")

    def test_invalid_statement(self):
        with self.assertRaises(ParseError):
            self.parser.parse_config_string("log_path:=")

        with self.assertRaises(ParseError):
            self.parser.parse_config_string("log_path=unterminated bar=foo")

    def test_unexpected_eol_parse(self):
        with self.assertRaises(ParseError):
            self.parser.parse_config_string("log_path=unterminated")


class TestBlocks(unittest.TestCase):
    def setUp(self):
        self.parser = ComfyParser()
        self.parser.add_setting("log_path", default="/var/log/my.log")
        block = self.parser.add_block("hostgroup", named=True)
        block.add_setting("hosts", required=True)
        block.add_setting(
            "timeout", default=datetime.timedelta(seconds=5),
            convert=lambda x: datetime.timedelta(seconds=float(x)),
            validate=lambda x: abs(x) == x
        )

    def test_single_line(self):
        config = self.parser.parse_config_string(
            "hostgroup 'web' {hosts=['node01','node02'];}"
        )
        self.assertTrue('hostgroup' in config)
        self.assertTrue(isinstance(config.hostgroup, dict))
        self.assertTrue('web' in config.hostgroup)
        self.assertTrue(isinstance(config.hostgroup['web'], Namespace))
        self.assertTrue(config.hostgroup['web'].hosts == ['node01','node02'])

    def test_invalid_block(self):
        with self.assertRaises(ParseError):
            config = self.parser.parse_config_string("hostgroup 'web' foo {")

    def test_invalid_list(self):
        with self.assertRaises(ParseError):
            config = self.parser.parse_config_string("hostgroup 'foo' { hosts=[:")

        with self.assertRaises(ParseError):
            config = self.parser.parse_config_string("hostgroup 'foo' {hosts=[ a b")

    def test_lexer_syntax_error(self):
        with self.assertRaises(ParseError):
            config = self.parser.parse_config_string("val'ue")


class TestNesting(unittest.TestCase):
    def setUp(self):
        self.parser = ComfyParser()
        self.parser.add_setting("nested_list")
        block = self.parser.add_block("nested")
        inner = block.add_block("inner")
        inner.add_block("deepest")

    def test_only_newlines(self):
        config = self.parser.parse_config_string("\n\n\n\n\n\n\n\n\n")


    def test_nested_list(self):
        config = self.parser.parse_config_string("nested_list:[[0,1],[1,0]];")
        self.assertTrue('nested_list' in config)
        self.assertTrue(config.nested_list == [['0','1'],['1','0']])

    def test_nested_blocks(self):
        config = self.parser.parse_config_string("""
            nested {
                inner {
                    deepest { }
                }
            }
        """)

        self.assertTrue(
            'nested' in config and isinstance(config.nested, Namespace)
        )
        self.assertTrue(
            'inner' in config.nested and isinstance(config.nested.inner, Namespace)
        )
        self.assertTrue(
            'deepest' in config.nested.inner and isinstance(config.nested.inner.deepest, Namespace)
        )


class TestMultiFile(unittest.TestCase):
    def setUp(self):
        os.mkdir('test.conf.d')
        self.parser = ComfyParser()
        lblock = self.parser.add_block("logging", required=True)
        lblock.add_setting("log_path", default="/var/log/test.log")
        lblock.add_setting("log_level", default=5, convert=int, validate=lambda x: abs(x) == x)
        gblock = self.parser.add_block("group", named=True)
        gblock.add_setting("hosts", required=True)
        gblock.add_setting("timeout",
            default=datetime.timedelta(seconds=5),
            convert=lambda x: datetime.timedelta(seconds=float(x)),
            validate=lambda x: abs(x) == x
        )
        with open("test.conf.d/main.conf", "w") as main_file:
            main_file.write("logging {}\n")
        with open("test.conf.d/core.conf", "w") as core_file:
            core_file.write("group 'infra' {\n\thosts=[\n\t\tfoo, 'bar'\n\t]\n}\n")

    def tearDown(self):
        shutil.rmtree('test.conf.d')

    def test_multiple_sources(self):
        config = self.parser.parse_config_files(glob.glob('test.conf.d/*.conf'))
        print(config)
