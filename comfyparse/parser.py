"""

    comfyparse.parser
    -----------------

    This module combines the components for declaring a configuration
    schema with the lexer which tokenizes a raw input string, and
    implements the grammar parser on top of them to parse an input into
    a ``Namespace`` and return it.
"""
import logging
import sys
from collections.abc import Callable, Sequence
from typing import Any, Optional, Union

from comfyparse.config import ConfigBlock, Namespace
from comfyparse.lexer import ComfyLexer, State as LexerState


logger = logging.getLogger("comfyparse")


class ParseError(Exception):
    """Raised when encountering an issue during parsing."""


class ComfyParser:
    """Creates a new ComfyParser object."""
    def __init__(self, name: Optional[str] = None, desc: str = ""):
        self._config_spec = ConfigBlock(
            name if name is not None else sys.argv[0], desc=desc, required=True
        )
        self._lineno = 1

    def add_setting(
            self, name: str, desc: str = "", required: bool = False,
            default: Optional[Any] = None, choices: Optional[Sequence] = None,
            convert: Optional[Callable[[Union[list, str]], Any]] = None,
            validate: Optional[Callable[[Any], bool]] = None) -> None:
        """Define a new global setting.

        :param name: The name of this setting.
        :param desc: A description of the setting. Included in automatic documentation.
        :param required: Whether the setting may be omitted. (Default ``False``)
        :param default: A value to use when the setting is omitted from a configuration.
        :param choices: Optionally, a list of allowed values for the setting.
        :param convert: Optionally, a callable which accepts the raw parsed value and
            returns an object of the appropriate type.
        :param validate: Optionally, a callable which accepts the (potentially converted)
            value and returns whether or not it is a valid value for the setting.

        :raise comfyparse.config.ConfigSpecError: Raised if the name is already in use.
        """
        self._config_spec.add_setting(
            name, desc, required, default, choices, convert, validate
        )

    def add_block(
            self, kind: str, named: bool = False, desc: str = "", required: bool = False,
            validate: Optional[Callable[[Namespace], bool]] = None) -> ConfigBlock:
        """Define and return a new global configuration block. 

        :param kind: The identifier for the block.
        :param named: If ``True``, multiple instances of a block can be included at the
            global configuration level. Each instance must include an additional name
            identifier to distinguish them. (Default ``False``)
        :param desc: A description of the block. Included in automatic documentation.
        :param required: Whether the block may be omitted. (Default ``False``)
        :param validate: Optionally, a callable which accepts the block after each field
            has been validated and returns whether or not is is valid.

        :raise comfyparse.config.ConfigSpecError: Raised if the kind identifier is already
            in use.

        The returned configuration block similarly supports the ``add_setting`` and 
        ``add_block`` methods to allow for hierarchical configuration construction.
        """
        return self._config_spec.add_block(kind, named, desc, required, validate)

    def generate_docs(self) -> str:
        """Returns a reStructuredText string consisting of documentation for the
        configuration's supported blocks and settings.
        """
        return self._config_spec.generate_docs()

    def parse_config_files(self, paths: list[str]) -> Namespace:
        """Given a list of file paths, open and parse each, combining the results into a
        single Namespace before returning the validated configuration Namespace.
        """
        result = Namespace()
        for path in paths:
            result.merge(self.parse_config_file(path, validate=False))
        return self.validate(result)

    def parse_config_file(self, path: str, validate: bool = True) -> Namespace:
        """Open and parse the contents of the given file path, returning the resulting
        configuration Namespace.
        """
        with open(path, 'r') as fp:
            return self.parse_config_string(fp.read(), validate=validate)

    def parse_config_string(self, data: str, validate: bool = True) -> Namespace:
        """Parse the contents of the given string, returning the resulting configuration
        Namespace. Setting ``validate`` to False omits the validation and conversion
        operations. This can be useful when constructing a configuration from multiple
        sources, where validation should only be invoked after the complete configuration
        object has been assembled, such as in ``ComfyParser.parse_config_files()``.
        """
        result = self._parse(data)
        return self.validate(result) if validate else result

    def validate(self, config: Namespace) -> Namespace:
        """Given an unvalidated Namespace, perform validation and return the resulting
        converted Namespace.
        """
        return self._config_spec.validate_block(config)

    def _parse(self, data: str) -> Namespace:
        lexer = ComfyLexer(data)
        try:
            lexer.tokenize()
        except SyntaxError as exc:
            raise ParseError(f"Invalid input at line {self._lineno}") from exc

        self._lineno = 1
        parsed = Namespace()
        block_stack = [parsed]

        def parse_expr() -> None:
            """Grammar: expr = [stmt/block]"""
            logger.debug("Line %s: Enter expr", self._lineno)
            parse_newline()
            if lexer.is_exhausted():
                return

            if lexer.peek(1).value in lexer.ASSIGNMENT:
                parse_stmt()
            else:
                parse_block()

            parse_newline()
            logger.debug("Line %s: Exit expr", self._lineno)

        def parse_block() -> None:
            """Grammar: block = string [string] '{' *expr '}'"""
            logger.debug("Line %s: Enter block", self._lineno)
            kind = lexer.consume()[0]
            if lexer.peek().value == '{':
                lexer.consume()
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
                raise ParseError(f"Invalid block syntax at line {self._lineno}")

            parse_newline()
            while lexer.peek().value != '}':
                parse_expr()
            lexer.consume()
            block_stack.pop()
            logger.debug("Line %s: Exit block", self._lineno)

        def parse_stmt() -> None:
            """Grammar: stmt = string ('=' / ':') value (';' / '\n')"""
            logger.debug("Line %s: Enter stmt", self._lineno)
            key = lexer.consume(2)[0]
            value = parse_value()
            if lexer.peek().value not in lexer.STMTEND:
                raise ParseError(f"Missing ';' or newline on line {self._lineno} after '{value}'")
            if lexer.peek().value == ';':
                lexer.consume()
            parse_newline()
            block_stack[-1][key.value] = value
            logger.debug("Line %s: Exit stmt", self._lineno)

        def parse_value() -> Union[str, list[str]]:
            """Grammar: value = list / string"""
            logger.debug("Line %s: Enter value", self._lineno)
            rval = parse_list() if lexer.peek().value == '[' else parse_string()
            logger.debug("Line %s: Exit value", self._lineno)
            return rval

        def parse_list() -> list:
            """Grammar: list = '[' value *(',' value) ']'"""
            logger.debug("Line %s: Enter list", self._lineno)
            lexer.consume() # Pull off the starting '['
            rval: list[Union[str, list]] = []
            while True:
                parse_newline() # Allow arbitrary newlines
                if lexer.peek().value == '[':
                    rval.append(parse_list()) # Support nested lists
                elif lexer.peek().kind == LexerState.STRING:
                    rval.append(parse_string())
                else:
                    raise ParseError(
                        "Unexpected token '{lexer.peek().value}' in list on line {self._lineno}"
                    )
                parse_newline()
                if lexer.peek().value not in ',]':
                    raise ParseError(f"Missing ',' or ']' at line {self._lineno}")
                token = lexer.consume()[0]
                if token.value == "]":
                    break
                parse_newline()

            logger.debug("Line %s: Exit list", self._lineno)
            return rval

        def parse_string() -> str:
            """A string is any set of characters. Follows shell parsing rules."""
            logger.debug("Line %s: Enter string", self._lineno)
            token = lexer.consume()[0]
            if token.kind != LexerState.STRING:
                raise ParseError(f"Expected string at line {self._lineno}, got {token.value}")
            self._lineno += token.value.count("\n") # Account for newlines in strings
            logger.debug("Line %s: Exit string", self._lineno)
            return token.value

        def parse_newline() -> None:
            while not lexer.is_exhausted() and lexer.peek().value == '\n':
                lexer.consume()
                self._lineno += 1

        try:
            while not lexer.is_exhausted():
                parse_expr()
        except IndexError as exc:
            raise ParseError("Unexpected EOF") from exc

        return parsed
