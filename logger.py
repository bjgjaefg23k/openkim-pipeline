"""
    from logger import logger

doing so, we'll have access to all of the constants as well as the logger which ought to be
made a child of eary::

    logger = logger.getChild("<child name>")
"""
import re
from pygments.lexer import RegexLexer, include
from pygments.token import Punctuation, Text, Comment, Keyword, Name, String, \
     Generic, Operator, Number, Whitespace, Literal, Error, Token
from pygments import highlight
from pygments.formatters import get_formatter_by_name
from pygments.style import Style
import sys
import os
import logging
import logging.handlers
import config as cf

__all__ = ['LogLexer']

FILELEVEL = logging.INFO

class LogStyle(Style):
    background_color = "#000000"
    highlight_color = "#222222"
    default_style = "#cccccc"

    styles = {
        Token:                     "#cccccc",
        Whitespace:                "",
        Comment:                   "#000080",
        Comment.Preproc:           "",
        Comment.Special:           "bold #2BB537",

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
    name = 'Logging.py Logs'
    aliases = ['log']
    filenames = ['*.log']
    mimetypes = ['text/x-log']

    flags = re.VERBOSE
    _logger = r'-\s(pipeline)(\.([a-z._\-0-9]+))*\s-'
    _kimid  = r"((?:[_a-zA-Z][_a-zA-Z0-9]*?_?_)?[A-Z]{2}_[0-9]{12}(?:_[0-9]{3})?)"
    _uuid   = r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
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
            (_uuid, Comment.Special),
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


def pygmentize(text, formatter='256', outfile=sys.stdout, style=LogStyle):
    lexer = LogLexer()
    fmtr = get_formatter_by_name(formatter, style=style)
    highlight(text, lexer, fmtr, outfile)

class PygmentHandler(logging.StreamHandler):
    """ A beanstalk logging handler """
    def __init__(self):
        super(PygmentHandler,self).__init__()

    def emit(self,record):
        """ Send the message """
        err_message = self.format(record)
        pygmentize(err_message)


def createLogger():
    logger = logging.getLogger("pipeline")
    logger.setLevel(FILELEVEL)

    # create the formatting style (with lines and times if verbose)
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    if cf.PIPELINE_DEBUG_VBS:
        log_formatter = logging.Formatter('%(filename)s:%(lineno)d _ %(asctime)s - %(levelname)s - %(name)s - %(message)s')

    #create a rotating file handler
    rotfile_handler = logging.handlers.RotatingFileHandler(os.path.join(cf.KIM_LOG_DIR,"pipeline.log"),
            mode='a', backupCount=5, maxBytes=10*1024*1024)
    rotfile_handler.setLevel(FILELEVEL)
    rotfile_handler.setFormatter(log_formatter)
    logger.addHandler(rotfile_handler)

    #create a console logger
    console_handler = PygmentHandler()
    console_handler.setLevel(logging.INFO)
    if cf.PIPELINE_DEBUG_VBS:
        console_handler.setLevel(logging.DEBUG)

    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

    return log_formatter

log_formatter = createLogger()

