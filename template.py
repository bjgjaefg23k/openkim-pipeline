"""
Holds the templating logic for the kim preprocessor
"""
import re, shutil, os
import repository as repo
import kimid
from config import *
logger = logger.getChild("template")

#==========================
# Keywords
#==========================


RE_KIMID    = "([A-Z]{2}_[0-9]{12}_?[0-9]{3}?)"   
RE_FILE     = re.compile(r"(@FILE\[(.*)\])")     # matches @FILE[stuff] and returns stuff
RE_MODEL    = re.compile(r"(@MODELNAME)")       # matches @MODELNAME as a word
#RE_DATA     = re.compile(r"@DATA\[(.*)\]\[(.*)\]{2}")      # matches @DATA[RD_XXXX_000] fill-in, etc
RE_DATA     = re.compile("(@DATA(?:\[" + RE_KIMID + "\])(?:\[" + RE_KIMID + "\])?(?:\[" + RE_KIMID + "\])?)")
RE_CLEANER  = re.compile("(@[A-Z]*\[)(.*)(\])") # to remove the @FILE[] and @DATA[]
RE_PATH     = re.compile("(@PATH\["+RE_KIMID+"\])") 
RE_TEST     = re.compile("(@TESTNAME)")


def get_file(string,testdir):
    """ If the string has a FILE directive, get the full path to the file, else return zero """
    match = re.match(RE_FILE,string)
    if match:
        part, filename = match.groups()
        logger.debug("Found @FILE directive match for %r",filename)
        return os.path.join(testdir,filename)


def data_from_match(match):
    groups = match.groups()
    try:
        if len(groups) == 2:
            #a 2 call is an rd
            part, rd = groups
            rd = kimid.promote_kimid(rd)
            data = repo.data_from_rd(rd)
            return str(data)
        if len(groups) == 3:
            # a 3 call is TR, PR
            part, tr, pr = groups
            tr = kimid.promote_kimid(tr)
            pr = kimid.promote_kimid(pr)
            data = repo.data_from_tr_pr(tr,pr)
            return str(data)
        if len(groups) == 4:
            # a 4 call is part,te,mo,pr
            part, te, mo, pr = groups
            te = kimid.promote_kimid(te)
            mo = kimid.promote_kimid(mo)
            pr = kimid.promote_kimid(pr)
            data = repo.data_from_te_mo_pr(te,mo,pr)
            return str(data)
    except KeyError:
        raise PipelineDataMissing, "We couldn't get the requested data"
    raise PipelineTemplateError, "I don't understand how to parse this: {}".format(match.groups())

def path_from_match(match):
    """ return the appropriate path for a match """
    part,kid = match.groups()
    #logger.debug("got a @PATH directive request for %r",kid)
    kid = kimid.promote_kimid(kid)
    path =  repo.get_path(kid)
    #logger.debug("thinks the path is %r",path)
    return path

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

processors = [testname_processor, path_processor, data_processor, modelname_processor]

def process_line(line,*args):
    """ Takes a string for the line and processes it """
    for processor in processors:
        line = processor(line,*args)
        #logger.debug("current line is: %r",line)
    return line

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

