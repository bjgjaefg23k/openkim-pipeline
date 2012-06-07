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
    symbols  = ['Cu', 'Ag', 'Au', 'Ni', 'Pd', 'Pt']
    surfaces = ['111', '112', '137']
    
    for surface in surfaces:
        for symbol in symbols:
            newname = template+"_copy"
            finname = prefix+"_"+surface+"_"+symbol
            shutil.copytree(template, newname) 
            ConvertName(newname, finname, driver, {"SYMBOL": symbol, "SURFACE": surface})
    
if __name__ == "__main__":
    CreateBatch("test_surfaces", "test_surface_energy", "TD_111111111111_000")
    ConvertBatch("test_surface_energy", "TE_111111111", "TD_111111111111_000")
