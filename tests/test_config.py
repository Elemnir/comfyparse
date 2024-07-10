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

    def test_merge(self):
        nsa = Namespace(
            val1="foo", val2={"suba":Namespace(),"subb":Namespace(a=0)}, val3=Namespace(a="a",b=5)
        )
        nsb = Namespace(
            val4="bar", val2={"subb":Namespace(a=5),"subc":Namespace()}, val3=Namespace(a="b",c=8)
        )

        nsa.merge(nsb)
        self.assertEqual(nsa.val1, "foo")
        self.assertEqual(nsa.val2["subb"].a, 5)
        self.assertEqual(nsa.val3.a, "b")
        self.assertEqual(nsa.val3.b, 5)
        self.assertEqual(nsa.val3.c, 8)
        self.assertEqual(nsa.val4, "bar")


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

    def test_named_and_required_error(self):
        with self.assertRaises(ConfigSpecError):
            self.block.add_block("bad_block", named=True, required=True)
