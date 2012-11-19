#! /usr/bin/env python
"""
Create all of the corresponding tests for this test driver
"""

import ase.data
import os
import random
import shutil
import itertools
import tempfile
from config import KIM_TESTS_DIR

#do this for all of the elements
symbols = ase.data.chemical_symbols
# and the cubic structures
structures = ['fcc','bcc','sc','diamond']

folder_template = next( x for x in os.listdir(".") if x != __file__ )

#create a temporary directory
tempdir = tempfile.mktemp()

def new_kim_number():
    # return a new kim number
    while True:
        kim_num = "{:012d}".format(random.randint(0,10**12-1))
        if all( [ kim_num not in test for test in os.listdir(KIM_TESTS_DIR) ] ):
            return kim_num


# for symbol, structure in itertools.product(symbol,structure):
for symbol, structure in [('Fe','fcc')]:
    trans_dict = { 'symbol': symbol, 'structure': structure, 'KIM': new_kim_number() }
    folder = folder_template.format(**trans_dict)
    shutil.copytree(folder_template, os.path.join(tempdir, folder))

    for fl in os.listdir(folder):
        # rename file
        newfl = fl.format(**trans_dict)
        shutil.move2(os.path.join(folder,fl),os.path.join(folder,newfl))

        # replace contents
        with open(newfl,'w') as newcontents:
            contents = open(newfl).read()
            contents.format(**trans_dict)
            newcontents.write(contents)




# os.rmdir(tempdir)
