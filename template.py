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
import re, shutil, os
from config import *
from logger import logging
logger = logging.getLogger("pipeline").getChild("template")
import kimobjects
import database
import kimquery

import jinja2, simplejson
from functools import partial

#==========================
# Keywords
#==========================
RE_KIMID    = r"((?:[_a-zA-Z][_a-zA-Z0-9]*?_?_)?[A-Z]{2}_[0-9]{12}(?:_[0-9]{3})?)"
RE_MODEL    = re.compile(r"(@MODELNAME)")       # matches @MODELNAME as a word
RE_DATA     = re.compile(r"(@DATA\[(.*?)\]\s*$)")
RE_PATH     = re.compile(r"(@PATH\[(.*?)\])")
RE_TEST     = re.compile(r"(@TESTNAME)")

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

template_environment.filters['json'] = partial(simplejson.dumps,indent=4)

#--------------------------------------------
# DATA directive handlers
#--------------------------------------------
def data_from_match(match,query_version=kimquery.query_mongo):
    """ Get the data from a re match """
    groups = match.groups()
    part, queryraw = groups
    query = simplejson.loads(queryraw)
    try:
        data = query_version(query)
    except PipelineQueryError as e:
        logger.error("Error executing query %r" % query)
        raise e
    return data

#----------------------------------------
# PATH directive handlers
#----------------------------------------
def path_from_match(match):
    """ return the appropriate path for a match """
    part,cand = match.groups()
    logger.debug("looking at cand: %r", cand)
    obj = kimobjects.kim_obj(cand)
    try:
        path = obj.executable
    except AttributeError:
        path = obj.path

    logger.debug("thinks the path is %r",path)
    return path

#-----------------------------------------
# Processors
#-----------------------------------------
def path_processor(line,model,test):
    """replace all path directives with the appropriate path"""
    return re.sub(RE_PATH,path_from_match,line)

def data_processor(line,model,test):
    """ replace all data directives with the appropriate path """
    return re.sub(RE_DATA,data_from_match,line)

def modelname_processor(line,model,test):
    """ replace all modelname directives with the appropriate path """
    return re.sub(RE_MODEL,model,line)

def testname_processor(line,model,test):
    """ replace testname directive with test name """
    return re.sub(RE_TEST,test,line)

processors = [testname_processor, modelname_processor, path_processor, data_processor]

def process_line(line,*args):
    """ Takes a string for the line and processes it, appling all processors """
    for processor in processors:
        line = processor(line,*args)
    return line

#-----------------------------------------
# Main Methods
#-----------------------------------------
def dependency_processor(line):
    matches = re.finditer(RE_KIMID, line)
    for match in matches:
        yield (True, match.groups()[0])

def dependency_check(inp, model=True):
    """ Given an input file
        find all of the data directives and obtain the pointers to the relevant data if it exists
        if it doesn't exist, return a false and a list of dependent tests

        outputs:
            ready - bool
            dependencies_good_to_go - list of kids
            dependencies_needed - tuple of tuples
    """
    logger.debug("running a dependancy check for %r", os.path.basename(os.path.dirname(inp.name)))
    ready, dependencies = (True, [])

    cands = []
    #try to find all of the possible dependencies
    for line in inp:
        matches = re.finditer(RE_KIMID, line)
        for match in matches:
            matched_code = match.string[match.start():match.end()]
            cands.append((True, kimobjects.kim_obj(matched_code)))

    if not cands:
        return (True, None, None)

    #cheap transpose
    candstranspose = zip(*cands)
    allready = all(candstranspose[0])

    if allready:
        return allready, candstranspose[1], None
    else:
        return allready, ( kid for ready,kid in cands if ready ), ( pair for ready, pair in cands if not ready )


def process(inp, model, test, modelonly= False):
    """ takes in a file like object and retuns a processed file like object, writing a copy to TEMP_INPUT_FILE """
    logger.info("attempting to process %r for (%r,%r)",inp,model.kim_code,test.kim_code)
    with test.in_dir():
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        with open(TEMP_INPUT_FILE,'w') as out:
            for line in inp:
                logger.debug("line to process is:\n\t %r",line)
                if modelonly:
                    newline = modelname_processor(line, model.kim_code, test.kim_code)
                else:
                    newline = process_line(line,model.kim_code,test.kim_code)
                if not newline.endswith('\n'):
                    newline = newline + "\n"
                logger.debug("new line is: %r",newline)
                out.write(newline)

        return open(TEMP_INPUT_FILE)

