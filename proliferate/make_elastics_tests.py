#!/usr/bin/python
import os, re, glob, sys
import string
import shutil
import tempfile
import datetime
import simplejson
from contextlib import nested
from rename import CreateMetaData,InFileTextReplacement,ConvertName,ConvertBatch

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

def CreateBatch(template, prefix, driver):
    import ase.data
    symbols  = ['Al', 'Au', 'Pt', 'Pd', 'W', 'V'] #ase.data.chemical_symbols
    lattices = ['sc', 'fcc', 'bcc', 'diamond']
    index = 0
    for lattice in lattices:
        for symbol in symbols:
            newname = template+"_copy"
            finname = prefix+"_"+lattice+"_"+symbol
            testsource = EnglishToKIMID("test_lattice_const_"+lattice+"_"+symbol)
            testmodel = EnglishToKIMID2("ex_model_"+symbol+"_P_LJ")
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
    CreateBatch("test_elastics", "test_elastic_consts", "TD_222222222222_000")
    ConvertBatch("test_elastic_consts", "TE_222222222", "TD_222222222222_000")

