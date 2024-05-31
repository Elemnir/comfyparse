import unittest

from comfyparse.config import (
    Namespace, ConfigSetting, ConfigBlock, ConfigSpecError, ValidationError
)


class TestNamespace(unittest.TestCase):
    def test_empty_str_render(self):
        self.assertEqual(str(Namespace()), "Namespace{}")

    def test_named_empty_str_render(self):
        self.assertEqual(str(Namespace(name="test")), "Namespace[test]{}")

    def test_missing_attribute_error(self):
        with self.assertRaises(AttributeError):
            value = Namespace().test

    def test_missing_key_error(self):
        with self.assertRaises(KeyError):
            value = Namespace()["test"]


class TestConfigSetting(unittest.TestCase):
    def test_choices(self):
        with self.assertRaises(ValidationError):
            ConfigSetting("test", choices=["a","b"]).validate_value("c")


class TestConfigBlock(unittest.TestCase):
    def setUp(self):
        self.block = ConfigBlock("test")
        self.block.add_setting("test_setting")
        self.block.add_block("test_block")

    def test_duplicate_name_use(self):
        with self.assertRaises(ConfigSpecError):
            self.block.add_setting("test_block")
    
    def test_duplicate_kind_use(self):
        with self.assertRaises(ConfigSpecError):
            self.block.add_block("test_setting")

    def test_setting_should_be_block(self):
        with self.assertRaises(ValidationError):
            self.block.validate_block(Namespace(test_block=""))

    def test_block_should_be_setting(self):
        with self.assertRaises(ValidationError):
            self.block.validate_block(Namespace(test_setting=Namespace()))

    def test_unknown_key(self):
        with self.assertRaises(ValidationError):
            self.block.validate_block(Namespace(not_real=""))

        with self.assertRaises(ValidationError):
            self.block.validate_block(Namespace(not_real=Namespace()))
