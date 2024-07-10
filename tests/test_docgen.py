import datetime
import unittest

from comfyparse import ComfyParser


GENERATED_DOCS = """MyProgram.conf
==========



It supports the following settings:

========= =============== ===========
   Name      Required/    Description
              Default    
========= =============== ===========
log_level **Required**    What level logging should occur at. I'm being overly verbose to
                          force multiline. (Choices: [0, 1, 2, 3, 4])
log_path  /var/log/my.log Path where logs will be written
========= =============== ===========

The following subblocks are required/supported:

debug
----------

Another block kind.

A ``debug`` block is required.

hostgroup
----------

A group of hostnames to act on.

Multiple ``hostgroup`` blocks can be defined and must include a name to distinguish them.

It supports the following settings:

======= ============ ===========
  Name   Required/   Description
          Default   
======= ============ ===========
hosts   **Required** 
timeout 0:00:05      
======= ============ ===========
"""


class TestDocGen(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 5000
        self.parser = ComfyParser("MyProgram.conf")
        self.parser.add_setting("log_path",
            default="/var/log/my.log",
            desc="Path where logs will be written"
        )
        self.parser.add_setting("log_level",
            desc="What level logging should occur at. I'm being overly verbose to force multiline.",
            required=True,
            choices=list(range(5)),
            convert=int)
        block = self.parser.add_block("hostgroup", named=True, desc="A group of hostnames to act on.")
        block.add_setting("hosts", required=True)
        block.add_setting(
            "timeout", default=datetime.timedelta(seconds=5),
            convert=lambda x: datetime.timedelta(seconds=float(x)),
            validate=lambda x: abs(x) == x
        )
        self.parser.add_block("debug", required=True, desc="Another block kind.")

    def test_documentation_generation(self):
        docs = self.parser.generate_docs()
        self.assertEqual(docs, GENERATED_DOCS)
