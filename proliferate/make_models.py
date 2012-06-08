#!/usr/bin/python
import os, re, glob
import string
import shutil
import tempfile
import datetime
import simplejson
from contextlib import nested
from rename import CreateMetaData,InFileTextReplacement,ConvertName,ConvertBatch

if __name__ == "__main__":
    ConvertBatch("ExampleLj", "MO_607867530", 
            "ExampleLj__MD_607867530900_000",{"ex_model_driver_P_LJ": "MD_607867530999_000"})
