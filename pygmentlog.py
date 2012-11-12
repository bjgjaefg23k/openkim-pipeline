import re
from bisect import bisect

from pygments.lexer import Lexer, LexerContext, RegexLexer, ExtendedRegexLexer, \
     bygroups, include, using, this, do_insertions
from pygments.token import Punctuation, Text, Comment, Keyword, Name, String, \
     Generic, Operator, Number, Whitespace, Literal, Error
from pygments.util import get_bool_opt
from pygments.lexers.other import BashLexer

__all__ = ['LogLexer']

class LogLexer(RegexLexer):
    """
    Lexer for IRC logs in *irssi*, *xchat* or *weechat* style.
    """

    name = 'Logging.py Logs'
    aliases = ['log']
    filenames = ['*.log']
    mimetypes = ['text/x-log']

    flags = re.VERBOSE 
    _logger = r'-\s(pipeline)\.([a-z._-]+)\s-'
    _kimid  = r"((?:[_a-zA-Z][_a-zA-Z0-9]*?_?_)?[A-Z]{2}_[0-9]{12}(?:_[0-9]{3})?)"
    _path   = r'(?:[a-zA-Z0-9_-]{0,}/{1,2}[a-zA-Z0-9_\.-]+)+'
    _debug  = r'DEBUG'
    _info   = r'INFO'
    _error  = r'ERROR'
    _date   = r'\d{4}-\d{2}-\d{2}'
    _time   = r'\d{2}:\d{2}:\d{2},\d{3}'
    _ws     = r'(?:\s|//.*?\n|/[*].*?[*]/)+'
    _json   = r'{.*}'

    tokens = {
        'whitespace': [
            (_ws, Text),
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),
            (r'\s-\s', Text)
        ],
        'root': [
            include('whitespace'),
            (_kimid, Generic.Prompt),
            (_logger, Generic.Emph),
            (_date, Generic.Output),
            (_time, Generic.Output),
            (_path, Generic.Subheading),
            (_json, Generic.Deleted),
            (_debug, Generic.Strong),
            (_info, Generic.Traceback),
            (_error, Generic.Error),
            ('[a-zA-Z_][a-zA-Z0-9_]*', Generic.Output),
            ("[.-]", Punctuation),
            (r"'", Punctuation)
        ]
    }

from pygments import __version__, highlight
from pygments.formatters import get_formatter_by_name
import sys

def pygmentize(text, formatter='256', outfile=sys.stdout):
    lexer = LogLexer()
    fmtr = get_formatter_by_name(formatter)
    highlight(text, lexer, fmtr, outfile)
