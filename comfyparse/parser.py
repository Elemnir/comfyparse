import logging
from collections.abc import Callable, Sequence
from typing import Any, Optional, Union

from comfyparse.config import ConfigBlock, Namespace
from comfyparse.lexer import ComfyLexer, State as LexerState


logger = logging.getLogger("comfyparse")


class ParseError(Exception):
    pass


class ComfyParser:
    def __init__(self):
        self._config_spec = ConfigBlock("GLOBAL")

    def add_setting(
            self, name: str, desc: str = "", required: bool = False,
            default: Optional[Any] = None, choices: Optional[Sequence] = None,
            convert: Optional[Callable[[Union[list, str]], Any]] = None,
            validate: Optional[Callable[[Any], bool]] = None) -> None:
        self._config_spec.add_setting(
            name, desc, required, default, choices, convert, validate
        )

    def add_block(
            self, kind: str, named: bool = False, desc: str = "", required: bool = False,
            validate: Optional[Callable[[Namespace], bool]] = None) -> ConfigBlock:
        return self._config_spec.add_block(kind, named, desc, required, validate)

    def parse_config_file(self, path: str) -> Namespace:
        with open(path, 'r') as fp:
            return self.parse_config_string(fp.read())

    def parse_config_string(self, data: str) -> Namespace:
        return self._parse(data)

    def _parse(self, data: str) -> Namespace:
        lexer = ComfyLexer(data)
        lexer.tokenize()
        lineno = 1
        parsed = Namespace()
        block_stack = [parsed]

        def parse_expr() -> None:
            logger.debug("enter expr")
            if lexer.peek().value == '\n':
                lexer.consume()
                lineno += 1
            elif lexer.peek(1).value in lexer.ASSIGNMENT:
                parse_stmt()
            else:
                parse_block()
            logger.debug("exit expr")

        def parse_block() -> None:
            logger.debug("enter block")
            kind = lexer.consume()[0]
            if lexer.peek().value == '{':
                new_block = Namespace()
                block_stack[-1][kind.value] = new_block
                block_stack.append(new_block)
            elif lexer.peek().kind == LexerState.STRING and lexer.peek(1).value == '{':
                name = lexer.consume(2)[0]
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
            lexer.consume()
            block_stack.pop()
            logger.debug("exit block")

        def parse_stmt() -> None:
            logger.debug("enter stmt")
            key = lexer.consume(2)[0]
            value = parse_value()
            if lexer.peek().value not in lexer.STMTEND:
                raise ParseError(f"Missing ';' or newline on line {lineno} after '{value}'")
            lexer.consume()
            block_stack[-1][key.value] = value
            logger.debug("exit stmt")

        def parse_value() -> Union[str, list[str]]:
            logger.debug("enter value")
            if lexer.peek().value == '[':
                return parse_list()
            return parse_string()

        def parse_list() -> list:
            logger.debug("enter list")
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
            logger.debug("exit list")
            return rval

        def parse_string() -> str:
            logger.debug("enter string")
            token = lexer.consume()[0]
            if token.kind != LexerState.STRING:
                raise ParseError(f"Expected string at line {lineno}, got {token.value}")
            logger.debug("exit string")
            return token.value

        try:
            while not lexer.is_exhausted():
                parse_expr()
        except IndexError as exc:
            raise ParseError("Unexpected EOF") from exc

        return self._config_spec.validate_block(parsed)
