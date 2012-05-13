""" This should contain some nice functions and methods for dealing
with the repository structure """

import sys, os, subprocess
from contextlib import contextmanager

#get the repository dir from the symlink
REPOSITORY_DIR = os.readlink('openkim-repository')

@contextmanager
def in_repo_dir():
    """Change to repo directory to execute code, then change back"""
    cwd = os.getcwd()
    os.chdir(REPOSITORY_DIR)
    yield
    os.chdir(cwd)

def pull(remote='origin',branch='master'):
    """ do a git pull """
    with in_repo_dir():
        return subprocess.call(['git','pull',remote,branch])

def push(remote='origin',branch='master'):
    """ do a git push """
    with in_repo_dir():
        return subprocess.call(['git','push',remote,branch])

