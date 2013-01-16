"""
Holds the templating logic for the kim preprocessor

The simple markup language as the following directives:

    * @FILE[filename] - if used in the output of a test, tells the pipeline
        to move the corresponding file
    * @MODELNAME - replaced by the pipeline with the running model's kimid, for use
        in the pipeline.in file so the test can execute the appropriate model
    * @PATH[kim_code] - for use in pipeline.in gives the path of the corresponding kim_code;
        the executable if its a test or a test driver, and the folder otherwise
    * @DATA[RD_2342...] - gives the data contained in the corresponding reference datum, the
        version is optional, if omitted get the latest version
    * @DATA[TR_232...][PR_2342...] - get the data stored for the PR code given in the test result (TR) code given
        both kim_codes can lack trailing versions, if so, get the latest
    * @DATA[TE_234...][MO_234...][PR_234...] - Get the data for the PR code given as a result of the specified TE, MO pair
        if it exists, if not, run it. version numbers can be ommited.
"""
import re, shutil, os
from config import *
logger = logger.getChild("template")
import kimobjects
import database

import jinja2, simplejson
from functools import partial


#==========================
# Keywords
#==========================

RE_KIMID    = r"((?:[_a-zA-Z][_a-zA-Z0-9]*?_?_)?[A-Z]{2}_[0-9]{12}(?:_[0-9]{3})?)"
#RE_KIMID = database.RE_KIMID
#RE_KIMID    = r"(?:[_a-zA-Z][_a-zA-Z0-9]*?__)?[A-Z]{2}_[0-9]{10,12}(?:_[0-9]{3})?"

RE_FILE     = re.compile(r"(@FILE\[(.*)\])")     # matches @FILE[stuff] and returns stuff
RE_MODEL    = re.compile(r"(@MODELNAME)")       # matches @MODELNAME as a word
#RE_DATA     = re.compile(r"@DATA\[(.*)\]\[(.*)\]{2}")      # matches @DATA[RD_XXXX_000] fill-in, etc
RE_DATA     = re.compile(r"(@DATA(?:\[" + RE_KIMID + r"\])(?:\[" +  RE_KIMID +  r"\])?(?:\[" + RE_KIMID + "\])?)")
#RE_CLEANER  = re.compile("(@[A-Z]*\[)(.*)(\])") # to remove the @FILE[] and @DATA[]
RE_PATH     = re.compile("(@PATH\[(.*?)\])")
RE_TEST     = re.compile("(@TESTNAME)")


#-----------------------------------------
# Jinja Stuff
#-----------------------------------------

template_environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader('/'),
        block_start_string='@[',
        block_end_string=']@',
        variable_start_string='@@',
        variable_end_string='@@',
        comment_start_string='@#',
        comment_end_string='#@',
        )

template_environment.filters['json'] = partial(simplejson.dumps,indent=4)


#-------------------------------------------
# FILE Directive handlers
#------------------------------------------


def files_from_results(results):
    """ Given a dictionary of results,
    return the filenames for any files contained in the results, from the @FILE directive """
    logger.debug("parsing results for file directives")
    testname = results["_testname"]
    test = kimobjects.Test(testname)
    #get only those files:that match the file directive, needs strings to process
    files = filter(None,(get_file(str(val),test.path) for key,val in results.iteritems()))
    return files

def get_file(string,testdir):
    """ If the string has a FILE directive, get the full path to the file, else return zero """
    match = re.match(RE_FILE,string)
    if match:
        part, filename = match.groups()
        logger.debug("Found @FILE directive match for %r",filename)
        return os.path.join(testdir,filename)

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
    logger.debug("trying to find data path for groups: %r",groups)
    if len(groups) == 2:
        # a 2 call is an rd
        part, rd_kcode = groups
        rd = kimobjects.ReferenceDatum(rd_kcode)
        return (True, rd)
    if len(groups) == 3:
        # a 3 call is TR, PR
        part, tr_kcode, pr_kcode = groups
        tr = kimobjects.TestResult(tr_kcode)
        return (True, tr)
    if len(groups) == 4:
        # a 4 call is part,te,mo,pr
        part, te_kcode, mo_kcode, pr_kcode = groups
        te = kimobjects.Test(te_kcode)
        mo = kimobjects.Model(mo_kcode)
        pr = kimobjects.Property(pr_kcode)
        try:
            tr = te.result_with_model(mo)
        except PipelineDataMissing:
            #tr doesn't exist
            return (False, [te,mo])
        else:
            return (True, tr)
    raise PipelineTemplateError, "didn't understand the in file"

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
        raise PipelineDataMissing, "We couldn't get the requested data"
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


def process(inp, modelname, testname, modelonly= False):
    """ takes in a file like object and retuns a processed file like object, writing a copy to TEMP_INPUT_FILE """
    logger.info("attempting to process %r for (%r,%r)",inp,modelname,testname)
    try:
        test = kimobjects.Test(testname)
    except AssertionError as e:
        try:
            test = kimobjects.Verifier(testname)
        except AssertionError as e:
            raise
    with test.in_dir():
        with open(TEMP_INPUT_FILE,'w') as out:
            for line in inp:
                logger.debug("line to process is:\n\t %r",line)
                if modelonly:
                    newline = modelname_processor(line, modelname, testname)
                else:
                    newline = process_line(line,modelname,testname)
                logger.debug("new line is: %r",newline)
                out.write(newline)

        return open(TEMP_INPUT_FILE)

