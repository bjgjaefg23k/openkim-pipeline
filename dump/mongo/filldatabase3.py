import pymongo
import os
import yaml
import json
from logger import logging
logger = logging.getLogger('pipeline').getChild('mongofill')
from processkimfiles import eatfile, configtojson
from database import parse_kim_code
import itertools

client = pymongo.MongoClient()
db = client.database

#tests = db.tests
#tests.insert(post)
REPO_DIR = os.path.abspath("/home/vagrant/openkim-repository/")

obj_db = db.obj
result_db = db.tr
error_db = db.er
verif_db = db.vr

def drop_tables():
    db['obj'].drop()
    db['tr'].drop()
    db['vr'].drop()
    db['er'].drop()

BADKEYS = { "kimspec", "profiling" }
def rmbadkeys(dd):
    return { k:v for k,v in dd.iteritems() if k not in BADKEYS }

def kimcode_to_dict(kimcode):
    name,leader,num,version = parse_kim_code(kimcode)
    leader = leader.lower()
    foo = { "name": name, "type": leader.lower(),
            "kimnum": num, "version": int(version),
            "shortcode": "_".join((leader.upper(),num)),
            "kimcode": kimcode,
            "path" : os.path.join(leader.lower(),kimcode),
            "approved" : True,
            '_id' : kimcode,
            }
    if foo['type'] in ('te','mo','md','vt','vm'):
        foo['makeable'] = True
    if foo['type'] in ('te','vt','vm'):
        foo['runner'] = True
    if foo['type'] in ('te','mo'):
        foo['subject'] = True
    if foo['type'] in ('md','td'):
        foo['driver'] = True
    else:
        foo['driver'] = False
    specpath = os.path.join(REPO_DIR,leader,kimcode,"kimspec.ini")
    spec = configtojson(specpath)
    if foo['type'] == 'te':
        try:
            testresult = spec['kimspec'].get('TEST_DRIVER_NAME')
            if testresult:
                foo['driver'] = rmbadkeys(kimcode_to_dict(testresult))
        except:
            pass
    if foo['type'] == 'mo':
        try:
            modeldriver = spec['kimspec'].get('MODEL_DRIVER_NAME')
            if modeldriver:
                foo['driver'] = rmbadkeys(kimcode_to_dict(modeldriver))
        except:
            pass
    foo.update(spec)
    return foo

def uuid_to_dict(leader,uuid):
    foo = {'uuid': uuid ,
            'path': os.path.join(leader.lower(),uuid),
            'type': leader,
            '_id' : uuid }
    spec = configtojson(os.path.join(REPO_DIR,leader,uuid,'kimspec.ini'))
    foo.update(spec)
    return foo

def doc_to_dict(doc,leader,uuid):
    foo = doc
    #copy info about result obj
    result_obj_doc = uuid_to_dict(leader,uuid)
    meta = rmbadkeys(result_obj_doc)

    if leader == 'tr':
        # IF wer are a TR get the test and model documents (cleaned up)
        runner = rmbadkeys(kimcode_to_dict(result_obj_doc['kimspec']['TEST_NAME']))
        subject = rmbadkeys(kimcode_to_dict(result_obj_doc['kimspec']['MODEL_NAME']))
    elif leader == 'vr':
        # IF we are a vr, get either the verification_Test or
        # verification_model and test or model
        runner_code = result_obj_doc['kimspec'].get('VERIFICATION_TEST',None)
        if not runner_code:
            runner_code = result_obj_doc['kimspec'].get('VERIFICATION_MODEL',None)
        if runner_code:
            runner = rmbadkeys(kimcode_to_dict(runner_code))

        subject_code = result_obj_doc['kimspec'].get('TEST_NAME',None)
        if not subject_code:
            subject_code = result_obj_doc['kimspec'].get('MODEL_NAME',None)
        if subject_code:
            subject = rmbadkeys(kimcode_to_dict(subject_code))
    try:
        meta['runner'] = runner
    except:
        pass
    try:
        meta['subject'] = subject
    except:
        pass
    foo['meta'] = meta
    return foo


def insert_objs():
    logger.info("Filling with objects")
    leaders = ('te','vt','vm','mo','md','td')
    for leader in leaders:
        for i,folder in enumerate(os.listdir(os.path.join(REPO_DIR,leader))):
            if folder.startswith("Make"):
                continue
            logger.info("On %d:%s ", i, folder)
            info = kimcode_to_dict(folder)
            try:
                db['obj'].insert(info)
            except:
                logger.error("Already have %s", folder)


def insert_results():
    logger.info("Filling with test results")
    leaders = ('tr','vr','er')
    for leader in leaders:
        for i, folder in enumerate(os.listdir(os.path.join(REPO_DIR,leader))):
            logger.info("On %d:%s ", i, folder)
            info = uuid_to_dict(leader,folder)
            try:
                resultobj = db['obj'].insert(info)
            except:
                logger.error("Aready have %s",folder)
                continue
            try:
                with open(os.path.join(REPO_DIR,leader,folder,'results.yaml')) as f:
                    yaml_docs = yaml.load_all(f)
                    for doc in yaml_docs:
                        stuff = doc_to_dict(doc,leader,folder)
                        db[leader].insert(stuff)
            except:
                logger.info("Could not read document for %s/%s", leader, folder)
                stuff = doc_to_dict({},leader,folder)
                db[leader].insert(stuff)


def insert_all():
    insert_objs()
    insert_results()

