import collections
import enum


Token = collections.namedtuple('Token', 'value, kind')

State = enum.Enum('State', ["READY", "VALUE", "STRING", "SYNTAX", "COMMENT"])


class ComfyLexer:
    WHITESPACE = "\t "
    COMMENT = "%#"
    SYNTAX = "{}[]=:,;\n"
    STMTEND = ";\n"
    ASSIGNMENT = "=:"
    QUOTES = "\'\""

    def __init__(self, source: str):
        self.state: State = State.READY
        self._source: str = source
        self._srcline: int = 0
        self._srcchar: int = 0

        self._tokens: list[Token] = []
        self._tknidx: int = 0

    def _peek_char(self, k: int=0) -> str:
        return self._source[self._srcchar + k]

    def _consume_char(self, k: int=1) -> str:
        char = self._source[self._srcchar]
        self._srcchar += k
        return char

    def _tokenize(self):
        try:
            token = ""
            while self._srcchar < len(self._source):
                if self.state == State.READY:
                    if self._peek_char() in self.WHITESPACE:
                        self._consume_char()
                    elif self._peek_char() in self.COMMENT:
                        self.state = State.COMMENT
                    elif self._peek_char() in self.SYNTAX:
                        self.state = State.SYNTAX
                    elif self._peek_char() in self.QUOTES:
                        self.state = State.STRING
                        token = self._consume_char()
                    else:
                        self.state = State.VALUE
                        token = self._consume_char()

                elif self.state == State.COMMENT:
                    if self._peek_char() != "\n":
                        self._consume_char()
                    else:
                        self._tokens.append(Token(self._consume_char(), State.SYNTAX))
                        self.state = State.READY

                elif self.state == State.SYNTAX:
                    self._tokens.append(Token(self._consume_char(), self.state))
                    self.state = State.READY

                elif self.state == State.STRING:
                    if self._peek_char() == "\\":
                        token += self._consume_char()
                        token += self._consume_char()
                    elif self._peek_char() == token[0]:
                        self._consume_char()
                        self._tokens.append(Token(token[1:], self.state))
                        self.state = State.READY
                    else:
                        token += self._consume_char()

                elif self.state == State.VALUE:
                    nchar = self._peek_char()
                    if nchar in self.WHITESPACE or nchar in self.COMMENT or nchar in self.SYNTAX:
                        self._tokens.append(Token(token, self.state))
                        self.state = State.READY
                    elif nchar in self.QUOTES:
                        raise SyntaxError("Unexpected quote in non-string token")
                    else:
                        token += self._consume_char()

            if self.state != State.READY:
                self._tokens.append(Token(token, self.state))

        except IndexError:
            raise SyntaxError("Unexpected EOF")

    def tokenize(self) -> None:
        if not self._tokens:
            self._tokenize()

    def peek(self, offset: int=0) -> Token:
        return self._tokens[self._tknidx + offset]

    def consume(self, num: int=1) -> list[Token]:
        tokens = self._tokens[self._tknidx:self._tknidx+num-1]
        self._tknidx += num
        return tokens

    def is_exhausted(self):
        return self._tknidx >= len(self._tokens)
