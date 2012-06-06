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
    if len(groups) == 2:
        #a 2 call is an rd
        part, rd = groups
        rd = kimid.promote_kimid(rd)
        data = repo.data_from_rd(rd)
        return str(data)
    if len(groups) == 3:
        # a 3 call is PR, PO
        part, pr, po = groups
        pr = kimid.promote_kimid(pr)
        po = kimid.promote_kimid(po)
        data = repo.data_from_pr_po(pr,po)
        return str(data)
    if len(groups) == 4:
        # a 4 call is part,te,mo,po
        part, te, mo, po = groups
        te = kimid.promote_kimid(te)
        mo = kimid.promote_kimid(mo)
        po = kimid.promote_kimid(po)
        data = repo.data_from_te_mo_po(te,mo,po)
        return str(data)
    raise KeyError, "I don't understand how to parse this"

def path_from_match(match):
    part,kid = match.groups()
    logger.debug("got a @PATH directive request for %r",kid)
    kid = kimid.promote_kimid(kid)
    return repo.get_path(kid)

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

def process_line(*args):
    """ Takes a string for the line and processes it """
    for processor in processors:
        line = processor(*args)
    return line

def process(inp, model, test):
    """ takes in a file like object and retuns a processed file like object """
    logger.info("attempting to process %r for (%r,%r)",inp,model,test)
    with open(TEMP_INPUT_FILE,'w') as out:
        for line in inp:
            newline = process_line(line,model,test)
            out.write(line)

    return open(TEMP_INPUT_FILE)

