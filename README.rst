============
 ComfyParse
============

What if ``configparser`` worked like ``argparse``?

ComfyParse provides a simple interface for declaratively defining the structure
of your program's configuration files. Files are written in a simple but 
flexible syntax inspired by the syntax used by Nginx for its configurations.
Like ``argparse``, ComfyParse automatically validates the configuration and can
be directed to convert the settings values from strings, returning a 
dictionary-like namespace object mirroring the structure of the configuration.
