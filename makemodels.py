#!/usr/bin/python
import os, re, glob
import string
import shutil
import tempfile
import datetime
import simplejson
from contextlib import nested


def CreateMetaData(name, oldname, driver):
    dic = {"kim_code": name, "title": oldname, "is_model_param": True, 
           "model_drivers": [driver], "reference": "", "disclaimer": "",
           "description": "Created using Mathematica data and the LJ driver",
           "license": "NONE", "uploaded_by": "sethna@lassp.cornell.edu",
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
    CreateMetaData(dst, src, "MD_607867530999_000")
    os.chdir("..")


def ConvertBatch(prefix, outprefix):
    index = 0
    for f in glob.glob("%s*" % prefix):
        outname = outprefix+"%02d_000" % index
        ConvertName(f, outname, {"ex_model_driver_P_LJ": "MD_607867530999_000"})
        index = index + 1

if __name__ == "__main__":
    ConvertBatch("ex_model", "MO_6078675309")
