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

import jinja2, simplejson
from functools import partial

#==========================
# Keywords
#==========================
RE_KIMID    = r"((?:[_a-zA-Z][_a-zA-Z0-9]*?_?_)?[A-Z]{2}_[0-9]{12}(?:_[0-9]{3})?)"
RE_MODEL    = re.compile(r"(@MODELNAME)")       # matches @MODELNAME as a word
RE_DATA     = re.compile(r"(@DATA\[(.*?)\])")
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
        )

template_environment.filters['json'] = partial(simplejson.dumps,indent=4)

#--------------------------------------------
# DATA directive handlers
#--------------------------------------------
def data_path_from_match(match):
    """ Given a match, try to find where it exists

    outputs:
        exists - bool
        path - either a kim_code, or a pair that must be run
    """
    groups = match.groups()
    logger.debug("trying to find data for groups: %r",groups)
    part, query = groups
    try:
         tr = te.result_with_model(mo)
    except Exception as e:
         return (False, [te,mo])
    return (True, tr)

def data_from_match(match):
    """ Get the data from a re match """
    groups = match.groups()
    logger.debug("looking at groups %r",groups)
    try:
        if len(groups) == 2:
            #a 2 call is an rd
            part, rd_kcode = groups
            rd = kimobjects.ReferenceDatum(rd_kcode)
            data = rd.data
            return data

        if len(groups) == 3:
            # a 3 call is TR, PR
            part, tr_kcode, pr_kcode = groups
            tr = kimobjects.TestResult(tr_kcode)
            pr = kimobjects.Property(pr_kcode)
            data = tr[pr]
            return str(data)
        if len(groups) == 4:
            # a 4 call is part,te,mo,pr
            part, te_kcode, mo_kcode, pr_kcode = groups
            te = kimobjects.Test(te_kcode)
            mo = kimobjects.Model(mo_kcode)
            pr = kimobjects.Property(pr_kcode)

            tr = te.result_with_model(mo)
            data = tr[pr.kim_code]
            return str(data)
    except KeyError:
        raise PipelineTemplateError, "I don't understand how to parse this: {}".format(match.groups())


#----------------------------------------
# PATH directive handlers
#----------------------------------------
def path_kim_obj_from_match(match):
    """ return the kim object of the path directive """
    part,cand = match.groups()
    logger.debug("looking at cand: %r", cand)
    obj = kimobjects.kim_obj(cand)
    return obj

def path_from_match(match):
    """ return the appropriate path for a match """
    obj = path_kim_obj_from_match(match)
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

def dependency_processor(line):
    """ find the data directives and get the location of data, if any, as generator """
    matches = re.finditer(RE_DATA,line)
    for match in matches:
        yield data_path_from_match(match)

def dependency_path_processor(line):
    """ get the paths of all PATH directives for dependency checking """
    matches = re.finditer(RE_PATH,line)
    for match in matches:
        yield (True, path_kim_obj_from_match(match))

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
        #logger.debug("current line is: %r",line)
    return line


#-----------------------------------------
# Main Methods
#-----------------------------------------
def dependency_check(inp, model=True):
    """ Given an input file
        find all of the data directives and obtain the pointers to the relevant data if it exists
        if it doesn't exist, return a false and a list of dependant tests

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
        if model:
            for cand in dependency_processor(line):
                cands.append(cand)
                logger.debug("found a candidate dependency: %r", cand)
        for path_cand in dependency_path_processor(line):
            cands.append(path_cand)
            logger.debug("found a path candidate dependency: %r", path_cand)

    if not cands:
        return (True, None, None)

    #cheap transpose
    candstranspose = zip(*cands)
    #is everyone ready?
    allready = all(candstranspose[0])

    if allready:
        #good to go
        return allready, candstranspose[1], None
    else:
        #grab the pairs
        return allready, ( kid for ready,kid in cands if ready ), ( pair for ready, pair in cands if not ready )


def process(inp, model, test, modelonly= False):
    """ takes in a file like object and retuns a processed file like object, writing a copy to TEMP_INPUT_FILE """
    logger.info("attempting to process %r for (%r,%r)",inp,model.kim_code,test.kim_code)
    with test.in_dir():
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

