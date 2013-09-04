import pymongo
import os, re
import yaml
import datetime
from ConfigParser import ConfigParser

from config import *
from logger import logging
logger = logging.getLogger('pipeline').getChild('mongodb')

client = pymongo.MongoClient()
db = client[MONGODB]

def config_ini(flname):
    c = ConfigParser()
    c.optionxform = str
    c.read(flname)
    data = {}
    for section in c.sections():
        data[section] = dict(c.items(section))
    return data

def config_yaml(flname):
    with open(flname) as f:
        doc = yaml.load(f)
        if isinstance(doc, dict) and not doc.has_key('kimspec'):
            out = {}
            out['kimspec'] = doc
            return out
        return doc

def parse_kim_code(kim_code):
    RE_KIMID = r"(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{12})(?:_([0-9]{3}))?"
    return re.match(RE_KIMID,kim_code).groups()

def drop_tables():
    check = raw_input("Are you sure? [y/n] ")
    if check == "y":
        db['obj'].drop()
        db['tr'].drop()
        db['vr'].drop()
        db['er'].drop()
        db['log'].drop()
        db['job'].drop()
        db['agent'].drop()

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
            "created_on": datetime.datetime.utcnow(),
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

    try:
        try:
            specpath = os.path.join(RSYNC_LOCAL_ROOT,leader,kimcode,"kimspec.ini")
            spec = config_yaml(specpath)
        except:
            specpath = os.path.join(RSYNC_LOCAL_ROOT,leader,kimcode,"kimspec.yaml")
            spec = config_yaml(specpath)
    except IOError as e:
        specpath = os.path.join(RSYNC_LOCAL_ROOT,leader,kimcode,"kimspec.ini")
        spec = config_ini(specpath)

    if foo['type'] == 'te':
        try:
            testresult = spec.get('test-driver')
            if testresult:
                foo['driver'] = rmbadkeys(kimcode_to_dict(testresult))
        except:
            pass
    if foo['type'] == 'mo':
        try:
            modeldriver = spec.get('model-driver')
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
            '_id' : uuid ,
            "created_on": datetime.datetime.utcnow(),
            }

    try:
        try:
            spec = config_yaml(os.path.join(RSYNC_LOCAL_ROOT,leader,uuid,'kimspec.ini'))
        except:
            spec = config_yaml(os.path.join(RSYNC_LOCAL_ROOT,leader,uuid,'kimspec.yaml'))
    except IOError as e:
        spec = config_ini(os.path.join(RSYNC_LOCAL_ROOT,leader,uuid,'kimspec.ini'))

    #Extend runner and subject
    runner = None
    subject = None
    if leader == 'tr' or leader=='er':
        # IF wer are a TR get the test and model documents (cleaned up)
        runner = rmbadkeys(kimcode_to_dict(spec['kimspec']['TEST_NAME']))
        subject = rmbadkeys(kimcode_to_dict(spec['kimspec']['MODEL_NAME']))
    elif leader == 'vr':
        # IF we are a vr, get either the verification_Test or
        # verification_model and test or model
        runner_code = spec['kimspec'].get('VERIFICATION_TEST',None)
        if not runner_code:
            runner_code = spec['kimspec'].get('VERIFICATION_MODEL',None)
        if runner_code:
            runner = rmbadkeys(kimcode_to_dict(runner_code))

        subject_code = spec['kimspec'].get('TEST_NAME',None)
        if not subject_code:
            subject_code = spec['kimspec'].get('MODEL_NAME',None)
        if subject_code:
            subject = rmbadkeys(kimcode_to_dict(subject_code))
    if runner:
        foo['runner'] = runner
    if subject:
        foo['subject'] = subject

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

def insert_one_object(kimcode):
    logger.info("Inserting object %s", kimcode)
    info = kimcode_to_dict(kimcode)
    try:
        db.obj.insert(info)
    except:
        logger.error("Already have %s", kimcode)

def insert_objs():
    logger.info("Filling with objects")
    leaders = ('te','vt','vm','mo','md','td')
    for leader in leaders:
        for i,folder in enumerate(os.listdir(os.path.join(RSYNC_LOCAL_ROOT,leader))):
            if folder.startswith("Make"):
                continue
            insert_one_object(folder)

def insert_one_result(leader, kimcode):
    logger.info("Inserting result %s ", kimcode)
    info = uuid_to_dict(leader, kimcode)
    try:
        resultobj = db.obj.insert(info)
    except:
        logger.error("Aready have %s", kimcode)
        return
    try:
        with open(os.path.join(RSYNC_LOCAL_ROOT,leader,kimcode,'results.yaml')) as f:
            yaml_docs = yaml.load_all(f)
            for doc in yaml_docs:
                stuff = doc_to_dict(doc,leader,kimcode)
                db.data.insert(stuff)
    except:
        logger.info("Could not read document for %s/%s", leader, kimcode)
        stuff = doc_to_dict({}, leader, kimcode)
        db.data.insert(stuff)


def insert_one_reference_data(leader, kimcode):
    logger.info("Inserting reference data %s ", kimcode)
    info = uuid_to_dict(leader, kimcode)
    try:
        resultobj = db.obj.insert(info)
    except:
        logger.error("Aready have %s", kimcode)
        return
    try:
        with open(os.path.join(RSYNC_LOCAL_ROOT,leader,kimcode,kimcode+'.yaml')) as f:
            yaml_docs = yaml.load_all(f)
            for doc in yaml_docs:
                stuff = doc_to_dict(doc,leader,kimcode)
                db.data.insert(stuff)
    except:
        logger.info("Could not read document for %s/%s", leader, kimcode)
        stuff = doc_to_dict({}, leader, kimcode)
        db.data.insert(stuff)


def insert_results():
    logger.info("Filling with test results")
    leaders = ('tr','vr','er')
    for leader in leaders:
        for i, folder in enumerate(os.listdir(os.path.join(RSYNC_LOCAL_ROOT,leader))):
            insert_one_result(leader, folder)

def insert_reference_data():
    logger.info("Filling with reference data")
    leaders = ('rd',)
    for leader in leaders:
        for i, folder in enumerate(os.listdir(os.path.join(RSYNC_LOCAL_ROOT,leader))):
            insert_one_reference_data(leader, folder)


def insert_all():
    insert_objs()
    insert_results()


def create_indices():
    """ Create the useful indices """
    db.obj.ensure_index("uuid")
    db.obj.ensure_index("kimcode")
    db.obj.ensure_index("type")
    db.obj.ensure_index("shortcode")
    db.obj.ensure_index("version")
    db.obj.ensure_index("driver.kimcode")
    db.obj.ensure_index("ensured_on")

    db.data.ensure_index("meta.type")
    db.data.ensure_index("meta.ensured_on")
    db.data.ensure_index("meta.runner.kimcode")
    db.data.ensure_index("meta.subject.kimcode")
    db.data.ensure_index("property")
    db.data.ensure_index("kim-template-tags")
    db.data.ensure_index("uuid")


