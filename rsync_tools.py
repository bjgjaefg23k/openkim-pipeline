"""
Simple set of tools for having rsync commands go through
"""

def temp_write(*args):
    """ write things to the temporary write area """

def temp_read(*args):
    """ pull things from the temporary read area """

def real_write(*args):
    """ FORBIDDEN:
        write things to the real write area """

def real_read(*args):
    """ read things from the real read directory """
