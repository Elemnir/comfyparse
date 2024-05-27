import enum
from typing import Union

from .config import ConfigBlock, Namespace
from .lexer import ComfyLexer, State as LexerState


class ParseError(Exception):
    pass


class ComfyParser:
    def __init__(self):
        self._config_spec = ConfigBlock("GLOBAL")
        self._config_values = Namespace()

    def add_setting(self, name, desc="", required=False, default=None, choices=None, convert=None, validate=None):
        self._config_spec.add_setting(name, desc, required, default, choices, convert, validate)

    def add_block(self, kind, named=False, desc="", required=False, validate=None):
        return self._config_spec.add_block(kind, named, desc, required, validate)

    def clear_config(self):
        self._config_values = Namespace()

    def parse_config_file(self, path):
        with open(path, 'r') as fp:
            return self.parse_config_string(fp.read())

    def parse_config_string(self, data):
        self._config_values = self._parse(data)
        return self._config_values

    def _parse(self, data: str) -> Namespace:
        lexer = ComfyLexer(data)
        lexer.tokenize()
        lineno = 1
        parsed = Namespace()
        block_stack = [parsed]

        def parse_expr() -> None:
            if lexer.peek().value == '\n':
                lexer.consume()
                lineno += 1
            elif lexer.peek(1).value in lexer.ASSIGNMENT:
                parse_stmt()
            else:
                parse_block()

        def parse_block() -> None:
            kind = lexer.consume()[0]
            if lexer.peek().value == '{':
                new_block = Namespace()
                block_stack[-1][kind.value] = new_block
                block_stack.append(new_block)
            elif lexer.peek().kind == LexerState.STRING and lexer.peek(1).value == '{':
                name, _ = lexer.consume(2)
                new_block = Namespace(name=name.value)
                try:
                    block_stack[-1][kind.value][name.value] = new_block
                except KeyError:
                    block_stack[-1][kind.value] = {name.value: new_block}
                block_stack.append(new_block)
            else:
                raise ParseError(f"Invalid block syntax at line {lineno}")

            while lexer.peek().value != '}':
                parse_expr()
            block_stack.pop()

        def parse_stmt() -> None:
            key, _ = lexer.consume(2)
            value = parse_value()
            if lexer.peek().value not in lexer.STMTEND:
                raise ParseError(f"Missing ';' or newline on line {lineno} after '{value}'")
            block_stack[-1][key.value] = value

        def parse_value() -> Union[str, list[str]]:
            if lexer.peek().value == '[':
                return parse_list()
            return parse_string()

        def parse_list() -> list:
            lexer.consume() # Pull off the starting '['
            rval: list[Union[str, list]] = []
            while True:
                if lexer.peek().value == '\n':
                    lexer.consume() # Allow arbitrary newlines
                    lineno += 1
                elif lexer.peek().value == '[':
                    rval.append(parse_list()) # Support nested lists
                elif lexer.peek().kind == LexerState.STRING:
                    rval.append(parse_string())
                    if lexer.peek().value not in ',]':
                        raise ParseError(f"Missing ',' or ']' at line {lineno}")
                    token = lexer.consume()[0]
                    if token.value == "]":
                        break
                else:
                    raise ParseError("Unexpected token '{}' in list on line {}".format(
                        lexer.peek().value, lineno
                    ))
            return rval

        def parse_string() -> str:
            token = lexer.consume()[0]
            if token.kind != LexerState.STRING:
                raise ParseError(f"Expected string at line {lineno}, got {token.value}")
            return token.value

        try:
            while not lexer.is_exhausted():
                parse_expr()
        except IndexError as exc:
            raise ParseError("Unexpected EOF") from exc

        return self._config_spec.validate(parsed)
