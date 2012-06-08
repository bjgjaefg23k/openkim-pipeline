#!/usr/bin/python
import os, re, glob, sys
import string
import shutil
import tempfile
import datetime
import simplejson
from contextlib import nested
from rename import CreateMetaData,InFileTextReplacement,ConvertName,ConvertBatch

"""
def EnglishToKIMID(eng):
    for f in glob.glob("/home/vagrant/openkim-repository/te/*/metadata.json"):
        dic = simplejson.load(open(f))
        if dic['title'] == eng:
            return dic['kim_code']
    return None

def EnglishToKIMID2(eng):
    for f in glob.glob("/home/vagrant/openkim-repository/mo/*/metadata.json"):
        dic = simplejson.load(open(f))
        if dic['title'] == eng:
            return dic['kim_code']
    return None
"""

def kim_id_from_prefix(prefix):
    matches = glob.glob(prefix+"*")
    if len(matches) == 1:
        return matches[0]
    else:
        raise IndexError, "%i matches found for prefix %s" %(len(matches), prefix)

def CreateBatch(template, prefix, driver):
    import ase.data
    #symbols  = ['Al', 'Au', 'Pt', 'Pd', 'W', 'V'] 
    symbols = ase.data.chemical_symbols
    lattices = ['sc', 'fcc', 'bcc', 'diamond']
    index = 0
    for lattice in lattices:
        for symbol in symbols:
            newname = template+"_copy"
            finname = prefix+string.capitalize(lattice)+symbol
            depend_test_prefix = "LatticeConstantCubic"+string.capitalize(lattice)+symbol
            depend_model_prefix = "ExampleLj"+symbol 
            try:
                testsource =kim_id_from_prefix(depend_test_prefix)
                testmodel = kim_id_from_prefix(depend_model_prefix)
            except:
                print "No matching test/model for lattice constant of ", lattice, symbol
                continue

            testproperty = "PR_000000000001_000"
            if testsource is not None and testmodel is not None:
                shutil.copytree(template, newname) 
                ConvertName(newname, finname, driver, {"SYMBOL": symbol, 
                    "LATTICE": lattice, "FILLINTEST": testsource, 
                    "FILLINMODEL": testmodel, "FILLINPROPERTY": testproperty})
            else:
                print testsource, testmodel, testproperty
                print "no english name"

if __name__ == "__main__":
    CreateBatch("test_elastics", "ElasticConstantsCubic", "TD_222222222222_000")
    ConvertBatch("ElasticConstantsCubic", "TE_222222222", "TD_222222222222_000")

