import unittest

from comfyparse.lexer import ComfyLexer


simple_valid_text = """
group servers {
    hosts = [ # end of line comments should work
        "node01", "node02'"
    ] % multiple flavors too
    timeout = 30.0f
}
log_path=/var/log/my.log
"""


simple_valid_tokens = [
    '\n', 'group', 'servers', '{', '\n', 'hosts', '=', '[', '\n', 'node01', ',',
    "node02'", '\n', ']', '\n', 'timeout', '=', '30.0f', '\n', '}', '\n',
    'log_path', '=', '/var/log/my.log', '\n'
]


class TestLexer(unittest.TestCase):
    def test_token_generation(self):
        lexer = ComfyLexer(simple_valid_text)
        lexer.tokenize()
        self.assertEqual([tk.value for tk in lexer._tokens], simple_valid_tokens)
