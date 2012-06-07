#!/usr/bin/python
import os, re, glob
import string
import shutil
import tempfile
import datetime
import simplejson
from contextlib import nested
from rename import CreateMetaData,InFileTextReplacement,ConvertName,ConvertBatch

def CreateBatch(template, prefix, driver):
    import ase.data
    symbols  = ['Al', 'Au', 'Pt', 'Pd', 'W', 'V'] #ase.data.chemical_symbols
    lattices = ['sc', 'fcc', 'bcc', 'diamond']
    
    for lattice in lattices:
        for symbol in symbols:
            newname = template+"_copy"
            finname = prefix+"_"+lattice+"_"+symbol
            shutil.copytree(template, newname) 
            ConvertName(newname, finname, driver, {"SYMBOL": symbol, "LATTICE": lattice})
    
if __name__ == "__main__":
    CreateBatch("test_lattices", "test_lattice_const", "TD_000000000001_000")
    ConvertBatch("test_lattice_const", "TE_000000000", "TD_000000000001_000")
