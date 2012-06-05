"""
Holds the templating logic for the kim preprocessor
"""

#==========================
# Keywords
#==========================

KW_FILE = "@FILE"


def get_file(str):
    """ If the str has a file directive, return the filename """
    if str.startswith(KW_FILE):
        pass

def get_modelname(str):
    """ process a modelname directive """

def process(file):
    """ takes in a file like object and retuns a processed file like object """


