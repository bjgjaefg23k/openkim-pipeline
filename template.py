"""
Holds the templating logic for the kim preprocessor
"""
import re

#==========================
# Keywords
#==========================

RE_FILE     = re.compile(r".*@FILE\[(.*?)\].*")     # matches @FILE[stuff] and returns stuff
RE_MODEL    = re.compile(r".*(@MODELNAME).*")       # matches @MODELNAME as a word
RE_DATA     = re.compile(r".*@DATA\[(.*)\].*")      # matches @DATA[RD_XXXX_000] fill-in, etc
RE_CLEANER  = re.compile(".*(@[A-Z]*\[)(.*)(\]).*") # to remove the @FILE[] and @DATA[]

def getmatch(match):
    if match is not None:
        return match.groups()
    return None

def replace_file_with_fullpath(str):
    """ If the str has a file directive, return the filename """
    match = getmatch(RE_FILE.match(str))
    if match:
         

def replace_modelname(str):
    """ process a modelname directive """


def process(file, model):
    """ takes in a file like object and retuns a processed file like object """


