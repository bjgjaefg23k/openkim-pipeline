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
    symbols  = ['Al', 'Cu', 'Ni', 'Pb', 'Ag'] #ase.data.chemical_symbols
    
    #boo = zip(ase.data.chemical_symbols, ase.data.reference_states)
    #[ elem for elem, state, in boo if (state and state['symmetry'] == 'fcc') ]
    for symbol in symbols:
        newname = template+"_copy"
        finname = prefix+"_"+symbol
        shutil.copytree(template, newname) 
        ConvertName(newname, finname, driver, {"SYMBOL": symbol})
    
if __name__ == "__main__":
    CreateBatch("test_bonds", "test_brokenbond_param", "TD_333333333333_000")
    ConvertBatch("test_brokenbond_param", "TE_333333333", "TD_333333333333_000")
