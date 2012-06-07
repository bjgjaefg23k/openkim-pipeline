#!/usr/bin/python
import os, re, glob, sys
import string
import shutil
import tempfile
import datetime
import simplejson
from contextlib import nested

def CreateMetaData(name, oldname, driver):
    dic = {"kim_code": name, "title": oldname, "is_model_param": True, 
           "test_drivers": [driver], "reference": "", "disclaimer": "",
           "description": "Lattice constant tests generated by Python using ASE & openkim-python",
           "license": "NONE", "uploaded_by": "alexalemi@gmail.com",
           "created_at": datetime.datetime.now().isoformat(), "updated_at": None}
    simplejson.dump(dic, open("metadata.json", "w"))


def InFileTextReplacement(filename, oldtxt, newtxt):
    tmpfile = ""
    with nested(open(filename, "r"), tempfile.NamedTemporaryFile("w", delete=False)) as (f,o):
        data = f.read()
        o.write( re.sub(oldtxt, newtxt, data) )
        tmpfile = o.name
    shutil.move(tmpfile, filename)


def ConvertName(src, dst, replacements=None):
    replacements = replacements or {}
    shutil.move(src, dst)   #os.system("mv %s %s" % (src, dst))  #mv $head $to
    os.chdir(dst)           #os.system("cd %s" % dst)            #cd $to
    for f in glob.glob("./%s*" % src):    # for file in `ls $head*`; do
        newf = string.replace(f, src, dst)  # newf=`echo $f|sed -e s/$head/$to/`
        shutil.move(f, newf)                # mv $f $newf
    for f in glob.glob("./*"):            # for f in `ls *`; do
        InFileTextReplacement(f, src, dst)
        for key,val in replacements.iteritems():
            InFileTextReplacement(f, key, val)
    CreateMetaData(dst, src, "TD_222222222222_000")
    os.chdir("..")


def ConvertBatch(prefix, outprefix):
    index = 0
    for f in glob.glob("%s*" % prefix):
        outname = outprefix+"%03d_000" % index
        ConvertName(f, outname) 
        index = index + 1

def EnglishToKIMID(eng):
    for f in glob.glob("/home/vagrant/openkim-repository/te/*/metadata.json"):
        dic = simplejson.load(open(f))
        if dic['title'] == eng:
            return dic['kim_code']
    return None

def CreateBatch(template, prefix):
    import ase.data
    symbols  = ['Al', 'Au', 'Pt', 'Pd', 'Ar', 'V'] #ase.data.chemical_symbols
    lattices = ['sc', 'fcc', 'bcc', 'diamond']
    index = 0
    for lattice in lattices:
        for symbol in symbols:
            newname = template+"_copy"
            finname = prefix+"_"+lattice+"_"+symbol
            testsource = EnglishToKIMID("test_lattice_const_"+lattice+"_"+symbol)
            if testsource is not None:
                shutil.copytree(template, newname) 
                ConvertName(newname, finname, {"SYMBOL": symbol, "LATTICE": lattice, "LATTICETEST": testsource})
            else:
                print "no english name"

if __name__ == "__main__":
    CreateBatch("test_elastics", "test_elastic_consts")
    ConvertBatch("test_elastic_consts", "TE_222222222")

