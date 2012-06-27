"""
Holds the templating logic for the kim preprocessor
"""
import re, shutil, os
from config import *
logger = logger.getChild("template")
import models
import database

#==========================
# Keywords
#==========================

RE_KIMID    = r"((?:[_a-zA-Z][_a-zA-Z0-9]*?_?_)?[A-Z]{2}_[0-9]{12}(?:_[0-9]{3})?)"   
#RE_KIMID = database.RE_KIMID
#RE_KIMID    = r"(?:[_a-zA-Z][_a-zA-Z0-9]*?__)?[A-Z]{2}_[0-9]{10,12}(?:_[0-9]{3})?"

RE_FILE     = re.compile(r"(@FILE\[(.*)\])")     # matches @FILE[stuff] and returns stuff
RE_MODEL    = re.compile(r"(@MODELNAME)")       # matches @MODELNAME as a word
#RE_DATA     = re.compile(r"@DATA\[(.*)\]\[(.*)\]{2}")      # matches @DATA[RD_XXXX_000] fill-in, etc
RE_DATA     = re.compile(r"(@DATA(?:\[" + RE_KIMID + r"\])(?:\[" + RE_KIMID + r"\])?(?:\[" + RE_KIMID + "\])?)")
#RE_CLEANER  = re.compile("(@[A-Z]*\[)(.*)(\])") # to remove the @FILE[] and @DATA[]
RE_PATH     = re.compile("(@PATH\[(.*?)\])")
RE_TEST     = re.compile("(@TESTNAME)")


#-------------------------------------------
# FILE Directive handlers
#------------------------------------------


def files_from_results(results):
    """ Given a dictionary of results,
    return the filenames for any files contained in the results """
    logger.debug("parsing results for file directives")
    testname = results["_testname"]
    test = models.Test(testname)
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
    
    RETRUNS:
        exists - bool
        path - either a kim_code, or a pair that must be run
    """
    groups = match.groups()
    logger.debug("trying to find data path for groups: %r",groups)
    if len(groups) == 2:
        # a 2 call is an rd
        part, rd_kcode = groups
        rd = models.ReferenceDatum(rd_kcode)
        return (True, rd)
    if len(groups) == 3:
        # a 3 call is TR, PR
        part, tr_kcode, pr_kcode = groups
        tr = models.TestResult(tr_kcode)
        return (True, tr)
    if len(groups) == 4:
        # a 4 call is part,te,mo,pr
        part, te_kcode, mo_kcode, pr_kcode = groups
        te = models.Test(te_kcode)
        mo = models.Model(mo_kcode)
        pr = models.Property(pr_kcode)
        try:
            tr = te.result_with_model(mo)
        except PipelineDataMissing:
            #tr doesn't exist
            return (False, [te,mo])
        else:
            return (True, tr)
    raise PipelineTemplateError, "didn't understand the in file"
        
def data_from_match(match):
    groups = match.groups()
    logger.debug("looking at groups %r",groups)
    try:
        if len(groups) == 2:
            #a 2 call is an rd
            part, rd_kcode = groups
            rd = models.ReferenceDatum(rd_kcode)
            data = rd.data
            return data

        if len(groups) == 3:
            # a 3 call is TR, PR
            part, tr_kcode, pr_kcode = groups
            tr = models.TestResult(tr_kcode)
            pr = models.Property(pr_kcode)
            data = tr[pr]
            return str(data)
        if len(groups) == 4:
            # a 4 call is part,te,mo,pr
            part, te_kcode, mo_kcode, pr_kcode = groups
            te = models.Test(te_kcode)
            mo = models.Model(mo_kcode)
            pr = models.Property(pr_kcode)

            tr = te.result_with_model(mo)
            data = tr[pr]
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
    obj = models.kim_obj(cand)
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
    matches = re.finditer(RE_PATH,line)
    for match in matches:
        yield (True, path_kim_obj_from_match(match))

def modelname_processor(line,model,test):
    """ replace all modelname directives with the appropriate path """
    return re.sub(RE_MODEL,model,line)

def testname_processor(line,model,test):
    """ replace testname directive with test name """
    return re.sub(RE_TEST,test,line)

processors = [testname_processor, path_processor, data_processor, modelname_processor]

def process_line(line,*args):
    """ Takes a string for the line and processes it """
    for processor in processors:
        line = processor(line,*args)
        #logger.debug("current line is: %r",line)
    return line


#-----------------------------------------
# Main Methods
#-----------------------------------------


def dependency_check(inp):
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


def process(inp, model, test):
    """ takes in a file like object and retuns a processed file like object """
    logger.info("attempting to process %r for (%r,%r)",inp,model,test)
    with open(TEMP_INPUT_FILE,'w') as out:
        for line in inp:
            #logger.debug("line to process is:\n\t %r",line)
            newline = process_line(line,model,test)
            #logger.debug("new line is:\n\t %r",newline)
            out.write(newline)

    return open(TEMP_INPUT_FILE)

