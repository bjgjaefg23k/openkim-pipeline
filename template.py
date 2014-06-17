"""
Holds the templating logic for the kim preprocessor

The simple markup language as the following directives:

    * @FILE[filename] - if used in the output of a test, tells the pipeline
        to move the corresponding file
    * @MODELNAME - replaced by the pipeline with the running model's kimid, for use
        in the pipeline.in file so the test can execute the appropriate model
    * @PATH[kim_code] - for use in pipeline.in gives the path of the corresponding kim_code;
        the executable if its a test or a test driver, and the folder otherwise
    * @DATA[string] - gives the data string returned by the query string
"""
import re
import os
import shutil

import ase.data
import jinja2, json, yaml, clj
from functools import partial

from kimquery import query
from kimunits import convert
import database
import kimobjects
from config import *
from logger import logging
logger = logging.getLogger("pipeline").getChild("template")


#-----------------------------------------
# New Template functions
#-----------------------------------------
def path(cand):
    obj = kimobjects.kim_obj(cand)
    try:
        p = obj.executable
    except AttributeError:
        p = obj.path

    logger.debug("thinks the path is %r",p)
    return p

def latestversion(kim):
    return database.format_kim_code(*database.get_latest_version(database.parse_kim_code(kim)))

def kimfinder(kim):
    return database.kim_code_finder(database.parse_kim_code(kim))[0]

def stripversion(kim):
    kimtup = database.parse_kim_code(kim)
    newtup = ( kimtup.name, kimtup.leader, kimtup.num, None)
    return database.format_kim_code( *newtup )

#custom yaml,json dump
yamldump = partial(yaml.dump, default_flow_style=False, explicit_start=True)
jsondump = partial(json.dumps, indent=4)
edndump  = partial(clj.dumps)

#-----------------------------------------
# Jinja Stuff
#-----------------------------------------
template_environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader('/'),
        block_start_string='@[',
        block_end_string=']@',
        variable_start_string='@<',
        variable_end_string='>@',
        comment_start_string='@#',
        comment_end_string='#@',
        undefined=jinja2.StrictUndefined,
        )

template_environment.filters.update(
        {
            "json": jsondump,
            "yaml": yamldump,
            "edn":  edndump,
            "stripversion": stripversion,
            "latestversion": latestversion,
        })

#add handy functions to global name space
template_environment.globals.update(
        {
            "path": path,
            "query": query,
            "convert": convert,
            "asedata": ase.data,
            "parse_kim_code": database.parse_kim_code,
            "kimfinder": kimfinder,
            "formatkimcode": database.format_kim_code,
        })

def process(inppath, model, test, modelonly=False, outfile=TEMP_INPUT_FILE):
    """ Takes in a path (relative to test directory)
    and writes a processed copy to TEMP_INPUT_FILE """
    logger.debug("attempting to process %r for (%r,%r)", inppath, test.kim_code, model.kim_code)

    with test.in_dir():
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        template = template_environment.get_template(inppath)
        extrainfo = {
                "TESTNAME": test.kim_code,
                "MODELNAME": model.kim_code,
            }
        output = template.render(**extrainfo)

        if not outfile:
            return output

        with open(outfile, 'w') as out:
                out.write(output)
