"""Pilgrim Syntax Generator

An update to the KantGenerator described in Mark Pilgrim's Dive Into Python.

This version uses lxml.etree instead of a SAX parser and argparse instead of getopt.
"""
import sys
from lxml import etree
from pathlib import Path
from random import choice
import argparse
import io

from psg import __version__


def open_anything(source):

    """URI, filename, or string --> stream

    This function lets you define parsers that take any input source
    (URL, pathname to local or network file, or actual data as a string)
    and deal with it in a uniform manner.  Returned object is guaranteed
    to have all the basic stdio read methods (read, readline, readlines).
    Just .close() the object when you're done with it.

    Examples:
    >>> from xml.dom import minidom
    >>> sock = openAnything("http://localhost/kant.xml")
    >>> doc = minidom.parse(sock)
    >>> sock.close()
    >>> sock = openAnything("c:\\inetpub\\wwwroot\\kant.xml")
    >>> doc = minidom.parse(sock)
    >>> sock.close()
    >>> sock = openAnything("<ref id='conjunction'><text>and</text><text>or</text></ref>")
    >>> doc = minidom.parse(sock)
    >>> sock.close()
    """
    if hasattr(source, "read"):
        return source

    if source == "-":
        import sys

        return sys.stdin

    # try to open with urllib (if source is http, ftp, or file URL)
    # import urllib
    # try:
    #     return urllib.urlopen(source)
    # except (IOError, OSError):
    #     pass

    # try to open with native open function (if source is pathname)
    try:
        return open(source)
    except (IOError, OSError):
        pass

    # treat source as string

    return io.StringIO(str(source))


class Generator:
    """Generates text based on a context-free grammar"""

    def __init__(self, grammar, source=None):
        self.parser = etree.XMLParser()
        self.load_grammar(grammar)
        self.load_source(source and source or self.get_default_source())
        self.refresh()

    def load_grammar(self, grammar):
        """load context-free grammar"""
        self.grammar = self._load(grammar)
        self.refs = {}
        for ref in self.grammar.findall("ref"):
            self.refs[ref.get("id")] = ref

    def _load(self, stuff):
        sock = open_anything(stuff)
        return etree.parse(sock, self.parser).getroot()

    def load_source(self, source):
        self.source = self._load(source)

    def get_default_source(self):
        """guess default source of the current grammar

        Default will be a single <ref> that is not cross-referenced.
        """
        xrefs = {}
        for xref in self.grammar.findall(".//xref"):
            xrefs[xref.get("id")] = 1
        xrefs = xrefs.keys()
        standalone_xrefs = [e for e in self.refs.keys() if e not in xrefs]
        if not standalone_xrefs:
            raise ValueError("can't guess source, and no source specified")
        xrefid = choice(standalone_xrefs)
        return f'<xref id="{xrefid}"/>'

    def reset(self):
        """reset the parser"""
        self.pieces = []
        self.capitalize_next_word = False

    def refresh(self):
        """reset output buffer, reparse entire source file, and return output"""
        self.reset()
        self.parse(self.source)
        return self.output()

    def output(self):
        """Output generated text"""
        return "".join(self.pieces)

    def random_child_element(self, node):
        return choice(node.getchildren())

    def parse(self, node):
        """parse a single xml node"""
        method = getattr(self, f"parse_{node.tag}")
        method(node)

    def parse_xref(self, node):
        self.parse(self.random_child_element(self.refs.get(node.get("id"))))
        self.pieces.append(node.tail or "")

    def parse_p(self, node):
        self.pieces.append(node.text or "")
        for child in node.iterchildren():
            self.parse(child)

grammar_rng = '''
<element name="grammar" xmlns="http://relaxng.org/ns/structure/1.0">
  <oneOrMore>
    <element name="ref">
      <attribute name="id"><text/></attribute>
      <oneOrMore>
        <element name="p">
            <oneOrMore>
              <mixed>
                  <optional>
                    <element name="xref">
                      <attribute name="id"/>
                    </element>
                  </optional>
              </mixed>
            </oneOrMore>
        </element>
      </oneOrMore>
    </element>
  </oneOrMore>
</element>
'''

def check_grammar(grammar):
    """check_grammar(grammar)
    Checks the grammar conforms to the grammar stadand using Relax-NG
    """
    relaxng_doc = etree.parse(io.StringIO(grammar_rng))
    relaxng = etree.RelaxNG(relaxng_doc)
    if relaxng.validate(etree.parse(open_anything(grammar)).getroot()):
        print("Grammer is valid")
    else:
        print(relaxng.error_log)

def main():
    grammar_dir = Path(__file__).parents[1] / "grammars"
    parser = argparse.ArgumentParser(
        description="Generates text based on a context-free grammar"
    )

    parser.add_argument(
        "--version",
        action="store_true",
        default=False,
        help="List version and quit"
    )

    commands = parser.add_subparsers(title="Commands", dest="command", metavar="")
    #commands.default = 'generate'
    lister = commands.add_parser(
            "list", help="list grammars", description="list available grammars"
            )
    generate = commands.add_parser(
        "generate", help="generate text", description="generates text from a grammar"
    )

    generate.add_argument("-g", "--grammar", default="binary")
    generate.add_argument(
        "source", nargs="?", help="Refence ID to start generation (optional)"
    )

    check = commands.add_parser(
        'check', help="check a grammar", description="validates a grammar file")
    check.add_argument('grammar')

    args, extras = parser.parse_known_args()
    if args.version:
        print(__version__)
        return 0

    if args.command == "list":
        print('\n'.join(str(p.stem) for p in grammar_dir.glob("*.xml")))
        sys.exit(0)

    if args.command == "check":
        grammar_path = grammar_dir / f"{args.grammar}.xml"
        sys.exit(check_grammar(grammar_path))

    if args.command is None:
        generate.parse_args(extras, namespace=args)

    grammar_path = grammar_dir / f"{args.grammar}.xml"
    if not grammar_path.exists():
        sys.exit("No grammar Found")

    if args.source:
        source = f'<xref id="{args.source}"/>'
    else:
        source = None

    g = Generator(grammar_path, source)
    print(g.output())


if __name__ == "__main__":
    sys.exit(main())
