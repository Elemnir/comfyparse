============
 ComfyParse
============

Configuration definition, parsing, and validation, in the style of ``argparse``.

ComfyParse provides a simple, declarative interface for defining the structure,
parsing, and validation of your project's configuration files. Its interface
design and functionality are intentionally similar to and inspired by that of
the ``argparse`` standard library. It provides built-in as well as custom
validation, hooks for converting settings values from text, and automatic help
documentation generation. Parsed configurations are returned as a dictionary-like
namespace object which mirrors the defined schema and supports both attribute as
well as index-based access.

::

    >>> import comfyparse
    >>> parser = comfyparse.ComfyParser()
    >>> parser.add_setting("myint", required=True, convert=int)
    >>> parser.add_setting("mystr", required=False, default="abc")
    >>> parser.parse_from_string("myint=10; mystr='foo';")
    Namespace{"myint": 10, "mystr": "foo"}
    >>> parser.parse_from_string("myint=10;")
    Namespace{"myint": 10, "mystr": "abc"}

ComfyParse uses its own syntax inspired by the syntax used by Nginx for its
configurations, resulting in a minimal but high expressive grammar. 
Like ``argparse``, ComfyParse automatically validates the configuration and can
be directed to convert the settings values from strings, returning a 
dictionary-like namespace object mirroring the structure of the configuration.

::

    group servers {
        hosts = [ # end of line comments work
            "node01", "node02"
        ] % multiple flavors too
        timeout = 30.0
    }
    log_path=/var/log/my.log

The configuration language consists of statements and blocks of statements. 
Statements assign a string or list value to a setting name, and can either be
terminated with a newline or a ``;``. Lists can be nested within lists, and
string values can use ``'`` and ``"`` as quotes for values or settings names
containing literal quotes, escape characters, or whitespace, or just for visual
differentiation.

Blocks have a type or "kind", and uses braces to encapsulate a set of statements.
Blocks can also contain sub-blocks, defined using the ``ConfigBlock.add_block()``
method. Blocks can also be defined to expect an additional name parameter to
differentiate between multiple blocks of the same kind such as the ``group`` block
named ``servers`` in the above example. Block kinds and names can optionally be
quoted if needed or desired.

Comments can be made using ``#`` or ``%`` characters which treats the rest of the
line as a comment. Either comment marker can be used interchangably within the
same document. Aside from newlines ending a comment or terminating a statement,
all whitespace is ignored and arbitrary.

The example below sets up ComfyParse to handle a document such as the example above.

::

    parser = comfyparse.ComfyParser("demoapp")
    parser.add_setting("log_path", desc="The path where logs go.", required=True)
    parser.add_setting("log_level", default=1, choices=[1,2,3,4,5], convert=int)
    group_block = parser.add_block("group", named=True, required=True)
    group_block.add_setting("hosts", required=True)
    group_block.add_setting("timeout", default=5.0, convert=float)


Once a schema such as this has been defined, configuration strings can be parsed as follows

::

    # Directly from a string
    config = parser.parse_config_string(confstr)
    # Alternatively, from a file path
    config = parser.parse_config_path("/path/to/file")

Lastly, the parser can generate a reStructuredText string outlining the schema for automatic documentation purposes, or just to provide a starting point when writing your own documentation.

::

    parser.generate_docs()


--------------
 Installation
--------------

ComfyParse can be installed using PyPI and requires no external dependencies.

::

    > pip install comfyparse

