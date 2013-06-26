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
db = client.test_database

#tests = db.tests
#tests.insert(post)
REPO_DIR = os.path.abspath("/home/vagrant/openkim-repository/")

objs = db.objs
results = db.results
errors = db.errors

def drop_tables():
    objs.drop()
    results.drop()
    errors.drop()

def kimcode_to_dict(kimcode):
    name,leader,num,version = parse_kim_code(kimcode)
    foo = { "kim-name": name, "kim-leader": leader,
            "kim-num": num, "kim-version": int(version),
            "kim-short": "_".join((leader,num)) }
    return foo

def insert_objs():
    logger.info("Filling with objects")
    leaders = ('te','vt','vm','mo','md','td')
    for leader in leaders:
        for i,folder in enumerate(os.listdir(os.path.join(REPO_DIR,leader))):
            if folder.startswith("Make"):
                continue
            logger.info("On %d:%s ", i, folder)
            path = os.path.join(REPO_DIR,leader,folder,"kimspec.ini")
            info = configtojson(path)
            info['kimid'] = folder
            info['path'] = os.path.join(leader,folder)
            info.update(kimcode_to_dict(folder))
            objs.insert(info)

def insert_results():
    logger.info("Filling with test results")
    leaders = ('tr','vr')
    for leader in leaders:
        for i, folder in enumerate(os.listdir(os.path.join(REPO_DIR,leader))):
            logger.info("On %d:%s ", i, folder)
            path = os.path.join(REPO_DIR,leader,folder)
            info = configtojson(os.path.join(path,'kimspec.ini'))
            info['path'] = os.path.join(leader,folder)
            info['uuid'] = folder
            resultobj = objs.insert(info)
            extra = {"meta" : {'path': os.path.join(leader,folder), 'uuid' : folder }, "parent" : resultobj }
            with open(os.path.join(path,'results.yaml')) as f:
                yaml_docs = yaml.load_all(f)
                # results.insert( ( dict(itertools.chain(doc.iteritems(),extra.iteritems())) for doc in yaml_docs) )
                for doc in yaml_docs:
                    doc.update(extra)
                    results.insert(doc)

def insert_errors():
    logger.info("Filling with errors results")
    leaders = ('er',)
    for leader in leaders:
        for i,folder in enumerate(os.listdir(os.path.join(REPO_DIR,leader))):
            logger.info("On %d:%s ", i, folder)
            path = os.path.join(REPO_DIR,leader,folder)
            info = configtojson(os.path.join(path,'kimspec.ini'))
            info['path'] = os.path.join(leader,folder)
            info['uuid'] = folder
            errors.insert(info)

