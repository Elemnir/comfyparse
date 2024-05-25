       
        

ParserState = enum.Enum("ParserState", [
    "START", "BLOCK", "STMT"
])

class ComfyParser():
    def __init__(self):
        _config = {}
        _known_idents = []
        _known_blocks = []

    def parse_paths(self, paths):
        for path in paths:
            new_conf = self._parse(path)
            self._config.update(new_conf)

    def _parse(self, path):
        
        with open(path, 'r') as fp:
            tokenizer = shlex.shlex(
                instream=fp, infile=path, posix=True, punctuation_chars=";{}[]=:,\n"
            )
            tokenizer.whitespace = " \t"
            tokenizer.whitespace_split = True
            while (token := tokenizer.get_token()) != tokenizer.eof:



