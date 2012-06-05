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
