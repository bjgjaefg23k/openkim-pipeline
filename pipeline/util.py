import os
import clj
import json
import subprocess
from functools import partial

jedns = partial(json.dumps, separators=(' ', ' '), indent=4)

def replace_nones(o):
    if isinstance(o, list):
        return [ replace_nones(i) for i in o ]
    elif isinstance(o, dict):
        return { k:replace_nones(v) for k,v in o.iteritems() }
    else:
        return o if o is not None else ''

def loadedn(f):
    """ this function tries to load something as edn: file, filename, string """
    if isinstance(f, basestring):
        try:
            f = open(f)
        except IOError as e:
            return clj.loads(f)
    return clj.load(f)

def dumpedn(o, f, allow_nils=True):
    if not allow_nils:
        o = replace_nones(o)
    o = jedns(o)

    if isinstance(f, basestring):
        with open(f, 'w') as fi:
            fi.write(o)
    else:
        f.write(o)

def mkdir_ext(p):
    if not os.path.exists(p):
        subprocess.check_call(['mkdir', '-p', p])
