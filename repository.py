""" This should contain some nice functions and methods for dealing
with the repository structure """

import sys, os, subprocess
from contextlib import contextmanager

#get the repository dir from the symlink
REPOSITORY_DIR = os.readlink('openkim-repository')

#define a repo_dir context manager
@contextmanager
def in_repo_dir():
    cwd = os.getcwd()
    os.chdir(REPOSITORY_DIR)
    yield
    os.chdir(cwd)


def pull_repo(remote='origin',branch='master'):
    """ do a git pull """
    with in_repo_dir():
        return subprocess.call(['git','pull',remote,branch])

def push_repo(remote='origin',branch='master'):
    with in_repo_dir():
        return subprocess.call(['git','push',remote,branch])

