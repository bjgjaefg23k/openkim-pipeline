#!/usr/bin/python
import os, re, glob
import string
import shutil
import tempfile
import datetime
import simplejson
from contextlib import nested
from rename import CreateMetaData,InFileTextReplacement,ConvertName,ConvertBatch


def ConvertBatch(prefix, outprefix, driver):
    index = 0
    for f in glob.glob("%s*" % prefix):
        outname = outprefix+"%02d_000" % index
        ConvertName(f, outname, driver, {"ex_model_driver_P_LJ": "MD_607867530999_000"})
        index = index + 1

if __name__ == "__main__":
    ConvertBatch("ex_model", "MO_6078675309", "MO_607867530999_000")
