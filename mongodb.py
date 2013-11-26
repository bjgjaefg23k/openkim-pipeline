import pymongo
import os, re
import datetime
import yaml
import datetime
from ConfigParser import ConfigParser

from config import *
import database
from logger import logging
logger = logging.getLogger('pipeline').getChild('mongodb')

client = pymongo.MongoClient(host='db0')
db = client[MONGODB]

PATH_RESULT = RSYNC_LOCAL_ROOT
PATH_APPROVED = RSYNC_LOCAL_ROOT

#PATH_RESULT = os.path.join(RSYNC_LOCAL_ROOT, "results")
#PATH_APPROVED = os.path.join(RSYNC_LOCAL_ROOT, "approved")

def config_yaml(flname):
    with open(flname) as f:
        doc = yaml.load(f)
        doc.setdefault("created_on", str(datetime.datetime.fromtimestamp(os.path.getctime(flname))))
        return doc

def parse_kim_code(kim_code):
    RE_KIMID = r"(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{12})(?:_([0-9]{3}))?"
    return re.match(RE_KIMID,kim_code).groups()

def drop_tables():
    check = raw_input("Are you sure? [y/n] ")
    if check == "y":
        db['obj'].drop()
        db['data'].drop()
        db['log'].drop()
        db['job'].drop()
        db['agent'].drop()
        db['data'].drop()

BADKEYS = { "kimspec", "profiling", "inserted_on", "latest" }
def rmbadkeys(dd):
    return { k:v for k,v in dd.iteritems() if k not in BADKEYS }

def flatten(o):
    if isinstance(o, dict):
        out = {}
        for key, value in o.iteritems():
            c = flatten(value)
            if isinstance(c, dict):
                out.update({key + "." + subkey: subval for subkey, subval in c.iteritems()})
            else:
                out.update({key: c})
        return out

    elif hasattr(o, "__iter__"):
        ll = [ flatten(item) for item in o ]
        return ll
    else:
        return o

def kimcode_to_dict(kimcode):
    dirpath = os.path.join(RSYNC_LOCAL_ROOT, leader, kimcode)

    name,leader,num,version = parse_kim_code(kimcode)
    if not name:
        name = database.look_for_name(leader, num, version)
        kimcode = database.format_kim_code(name, leader, num, version)

    leader = leader.lower()
    foo = { "name": name, "type": leader.lower(),
            "kimnum": num, "version": int(version),
            "shortcode": "_".join((leader.upper(),num)),
            "kimcode": kimcode,
            "path" : os.path.join(leader.lower(),kimcode),
            "approved" : True,
            "created_at" : datetime.datetime.fromtimestamp( os.path.getctime( dirpath )),
            '_id' : kimcode,
            "inserted_on": str(datetime.datetime.utcnow()),
            "latest": True,
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

    specpath = os.path.join(PATH_APPROVED,leader,kimcode,CONFIG_FILE)
    spec = config_yaml(specpath)

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
    dirpath = os.path.join(RSYNC_LOCAL_ROOT,leader,uuid)
    foo = {'uuid': uuid ,
            'path': os.path.join(leader.lower(),uuid),
            'type': leader,
            '_id' : uuid ,
            "inserted_on": str(datetime.datetime.utcnow()),
            "latest": True,
            }

    specpath = os.path.join(PATH_RESULT,leader,uuid,CONFIG_FILE)
    spec = config_yaml(specpath)

    pipespec = {}
    try:
        pipespecpath = os.path.join(PATH_RESULT,leader,uuid,PIPELINESPEC_FILE)
        pipespec = config_yaml(pipespecpath)
    except:
        pass

    #Extend runner and subject
    runner = None
    subject = None
    if leader == 'tr' or leader=='er':
        # IF wer are a TR get the test and model documents (cleaned up)
        runner = rmbadkeys(kimcode_to_dict(spec['test']))
        subject = rmbadkeys(kimcode_to_dict(spec['model']))
    elif leader == 'vr':
        # IF we are a vr, get either the verification_Test or
        # verification_model and test or model
        runner_code = spec.get('verification-test',None)
        if not runner_code:
            runner_code = spec.get('verification-model',None)
        if runner_code:
            runner = rmbadkeys(kimcode_to_dict(runner_code))

        subject_code = spec.get('test',None)
        if not subject_code:
            subject_code = spec.get('model',None)
        if subject_code:
            subject = rmbadkeys(kimcode_to_dict(subject_code))
    if runner:
        foo['runner'] = runner
    if subject:
        foo['subject'] = subject

    foo.update(spec)
    foo.update(pipespec)
    return foo


def doc_to_dict(doc,leader,uuid):
    foo = doc
    #copy info about result obj
    result_obj_doc = uuid_to_dict(leader,uuid)
    meta = rmbadkeys(result_obj_doc)

    if leader == 'tr':
        # IF wer are a TR get the test and model documents (cleaned up)
        runner = rmbadkeys(kimcode_to_dict(result_obj_doc['test']))
        subject = rmbadkeys(kimcode_to_dict(result_obj_doc['model']))
    elif leader == 'vr':
        # IF we are a vr, get either the verification_Test or
        # verification_model and test or model
        runner_code = result_obj_doc.get('verification-test',None)
        if not runner_code:
            runner_code = result_obj_doc.get('verification-model',None)
        if runner_code:
            runner = rmbadkeys(kimcode_to_dict(runner_code))

        subject_code = result_obj_doc.get('test',None)
        if not subject_code:
            subject_code = result_obj_doc.get('model',None)
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
    foo['created_on'] = result_obj_doc['created_on']
    foo['inserted_on'] = result_obj_doc['inserted_on']
    foo['latest'] = True
    return foo

def deprecate_similar_objects(dbname, info, keys):
    tinfo = flatten(info)
    query = { key:tinfo[key] for key in keys }
    query.update({'created_on': {"$lt": tinfo['created_on']}})
    update = { "$set": {"latest": False } }
    status = db[dbname].update(spec=query, document=update, multi=True)
    if status['n'] > 0:
        logger.info("Updated %i existing documents to deprecated" % status['n'])

def insert_one_object(kimcode):
    logger.info("Inserting object %s", kimcode)
    info = kimcode_to_dict(kimcode)
    try:
        db.obj.insert(info)
        deprecate_similar_objects('obj', info, ['shortcode'])
    except:
        logger.error("Already have %s", kimcode)

def insert_one_result(leader, kimcode):
    logger.info("Inserting result %s ", kimcode)
    stuff = None
    info = uuid_to_dict(leader, kimcode)
    try:
        resultobj = db.obj.insert(info)
        deprecate_similar_objects('obj', info, ['runner.kimcode', 'subject.kimcode'])
    except:
        logger.error("Aready have %s", kimcode)
        return
    try:
        with open(os.path.join(PATH_RESULT,leader,kimcode,'results.yaml')) as f:
            yaml_docs = yaml.load_all(f)
            for doc in yaml_docs:
                stuff = doc_to_dict(doc,leader,kimcode)
                db.data.insert(stuff)
        deprecate_similar_objects('data', stuff, ['meta.runner.kimcode', 'meta.subject.kimcode'])
    except:
        logger.info("Could not read document for %s/%s", leader, kimcode)
        stuff = doc_to_dict({}, leader, kimcode)
        db.data.insert(stuff)
        deprecate_similar_objects('data', stuff, ['meta.runner.kimcode', 'meta.subject.kimcode'])

def insert_one_reference_data(leader, kimcode):
    logger.info("Inserting reference data %s ", kimcode)
    info = kimcode_to_dict(leader, kimcode)
    try:
        resultobj = db.obj.insert(info)
    except:
        logger.error("Aready have %s", kimcode)
        return
    try:
        with open(os.path.join(PATH_APPROVED,leader,kimcode,kimcode+'.yaml')) as f:
            yaml_docs = yaml.load_all(f)
            for doc in yaml_docs:
                stuff = doc_to_dict(doc,leader,kimcode)
                db.data.insert(stuff)
    except:
        logger.info("Could not read document for %s/%s", leader, kimcode)
        stuff = doc_to_dict({}, leader, kimcode)
        db.data.insert(stuff)

def insert_objs():
    logger.info("Filling with objects")
    leaders = ('te','vt','vm','mo','md','td')
    for leader in leaders:
        for i,folder in enumerate(os.listdir(os.path.join(PATH_APPROVED,leader))):
            if folder.startswith("Make"):
                continue
            insert_one_object(folder)

def insert_results():
    logger.info("Filling with test results")
    leaders = ('tr','vr','er')
    for leader in leaders:
        for i, folder in enumerate(os.listdir(os.path.join(PATH_RESULT,leader))):
            insert_one_result(leader, folder)

def insert_reference_data():
    logger.info("Filling with reference data")
    leaders = ('rd',)
    for leader in leaders:
        for i, folder in enumerate(os.listdir(os.path.join(PATH_APPROVED,leader))):
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


