"""
Holds the templating logic for the kim preprocessor

We utilize jinja2 templating to expose certain functions to the templating
functionality of the pipeline.  As of this version, the following functions
are available

    * query(query) - run a general API query to query.openkim.org for any information
        including test results or reference data.  See query.openkim.org for
        information on formatting these queries
    * MODELNAME - a global variable which represents the current model coupling
        for this particular test run
    * TESTNAME - the current runing testname, similar to MODELNAME
    * path(kim_code) - gives the path of the corresponding kim_code;
        the executable if its a test or a test driver, and the folder otherwise
    * convert(value, srcunit, dstunit) - convert a floating point value from
        one unit to another
    * asedata - the dictionary of reference data contained within ASE
"""
import os
import ase.data
import jinja2
import json
import clj
from functools import partial

from kimquery import query
from kimunits import convert
import database
import kimobjects
import config as cf
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

#custom json dump
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

def process(inppath, model, test, modelonly=False, outfile=cf.TEMP_INPUT_FILE):
    """ Takes in a path (relative to test directory)
    and writes a processed copy to TEMP_INPUT_FILE """
    logger.debug("attempting to process %r for (%r,%r)", inppath, test.kim_code, model.kim_code)

    with test.in_dir():
        if not os.path.exists(cf.OUTPUT_DIR):
            os.makedirs(cf.OUTPUT_DIR)

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
