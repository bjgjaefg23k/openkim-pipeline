import re
from bisect import bisect

from pygments.lexer import Lexer, LexerContext, RegexLexer, ExtendedRegexLexer, \
     bygroups, include, using, this, do_insertions
from pygments.token import Punctuation, Text, Comment, Keyword, Name, String, \
     Generic, Operator, Number, Whitespace, Literal, Error
from pygments.util import get_bool_opt
from pygments.lexers.other import BashLexer

__all__ = ['LogLexer']

from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Token


class LogStyle(Style):
    """
    Styles somewhat like vim 7.0
    """

    background_color = "#000000"
    highlight_color = "#222222"
    default_style = "#cccccc"

    styles = {
        Token:                     "#cccccc",
        Whitespace:                "",
        Comment:                   "#000080",
        Comment.Preproc:           "",
        Comment.Special:           "bold #cd0000",

        Keyword:                   "#cdcd00",
        Keyword.Declaration:       "#00cd00",
        Keyword.Namespace:         "#cd00cd",
        Keyword.Pseudo:            "bold #00cd00",
        Keyword.Type:              "#00cd00",

        Operator:                  "#3399cc",
        Operator.Word:             "#cdcd00",

        Name:                      "",
        Name.Class:                "#00cdcd",
        Name.Builtin:              "#cd00cd",
        Name.Exception:            "bold #666699",
        Name.Variable:             "#00cdcd",

        String:                    "#cd0000",
        Number:                    "#cd00cd",

        Punctuation:               "nobold #FFF",
        Generic.Heading:           "nobold #FFF",
        Generic.Subheading:        "#800080",
        Generic.Deleted:           "nobold #cd3",
        Generic.Inserted:          "#00cd00",
        Generic.Error:             "bold #FF0000",
        Generic.Emph:              "bold #FFFFFF",
        Generic.Strong:            "bold #FFFFFF",
        Generic.Prompt:            "bold #3030F0",
        Generic.Output:            "#888",
        Generic.Traceback:         "bold #04D",

        Error:                     "border:#FF0000"
    }


class LogLexer(RegexLexer):
    """
    Lexer for IRC logs in *irssi*, *xchat* or *weechat* style.
    """

    name = 'Logging.py Logs'
    aliases = ['log']
    filenames = ['*.log']
    mimetypes = ['text/x-log']

    flags = re.VERBOSE 
    _logger = r'-\s(pipeline)(\.([a-z._\-0-9]+))+\s-'
    _kimid  = r"((?:[_a-zA-Z][_a-zA-Z0-9]*?_?_)?[A-Z]{2}_[0-9]{12}(?:_[0-9]{3})?)"
    _path   = r'(?:[a-zA-Z0-9_-]{0,}/{1,2}[a-zA-Z0-9_\.-]+)+'
    _debug  = r'DEBUG'
    _info   = r'INFO'
    _error  = r'ERROR'
    _pass   = r'PASS'
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
            (_pass, Keyword.Pseudo),
            (r'[0-9]+', Generic.Heading),
            ('[a-zA-Z_][a-zA-Z0-9_]*', Generic.Heading),
            (r'[{}`()\"\[\]@.,:-\\]', Punctuation),
            (r'[~!%^&*+=|?:<>/-]', Punctuation),
            (r"'", Punctuation)
        ]
    }

from pygments import __version__, highlight
from pygments.formatters import get_formatter_by_name
import sys

def pygmentize(text, formatter='256', outfile=sys.stdout, style=LogStyle):
    lexer = LogLexer()
    fmtr = get_formatter_by_name(formatter, style=style)
    highlight(text, lexer, fmtr, outfile)

if __name__ == "__main__":
    pygmentize(open("/home/vagrant/openkim-pipeline/logs/test.log").read()+"\n `{}ERROR - needed more output")
