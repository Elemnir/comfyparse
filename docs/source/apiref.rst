API Reference
*************

The intended interaction with ComfyParse is to create a ``ComfyParser`` instance, populate its schema with blocks and settings, and then parse one or more configuration documents with it to receive a ``Namespace`` object containing the parsed, validated, and converted configuration within those documents.

.. autoclass:: comfyparse.ComfyParser
   :members:

.. autoclass:: comfyparse.Namespace
   :members:


Exceptions
----------

The following custom exception types may occur when using ComfyParse:

.. autoclass:: comfyparse.parser.ParseError

.. autoclass:: comfyparse.config.ConfigSpecError

.. autoclass:: comfyparse.config.ValidationError


Internals
---------

You shouldn't need to interact with these components directly, but they are documented here for the sake of completeness. 

.. autoclass:: comfyparse.config.ConfigSetting
   :members:

.. autoclass:: comfyparse.config.ConfigBlock
   :members:

.. autoclass:: comfyparse.lexer.ComfyLexer
   :members:
