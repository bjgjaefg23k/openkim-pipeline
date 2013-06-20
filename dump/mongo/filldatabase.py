import pymongo
import os
import yaml
import json
from logger import logging
logger = logging.getLogger('pipeline').getChild('mongofill')
from processkimfiles import eatfile, configtojson

client = pymongo.MongoClient()
db = client.test_database

#tests = db.tests
#tests.insert(post)
REPO_DIR = os.path.abspath("/home/vagrant/openkim-repository/")

# results = db.results
# results.drop()
# logger.info("Filling with test results")
# leaders = ('tr','vr')
# for leader in leaders:
#     for folder in os.listdir(os.path.join(REPO_DIR,leader)):
#         logger.info("On %s ", folder)
#         path = os.path.join(REPO_DIR,leader,folder)
#         info = configtojson(os.path.join(path,'kimspec.ini'))
#         info['path'] = os.path.join(leader,folder)
#         with open(os.path.join(path,'results.yaml')) as f:
#             yaml_docs = yaml.load_all(f)
#             try:
#                 for prop in yaml_docs:
#                     z = info.copy()
#                     z.update(prop)
#                     results.insert(z)
#             except:
#                 logger.error("Error on document in %r", path)
#                 pass

# errors = db.errors
# errors.drop()
# logger.info("Filling with errors results")
# leaders = ('er',)
# for leader in leaders:
#     for folder in os.listdir(os.path.join(REPO_DIR,leader)):
#         logger.info("On %s ", folder)
#         path = os.path.join(REPO_DIR,leader,folder)
#         info = configtojson(os.path.join(path,'kimspec.ini'))
#         info['path'] = os.path.join(leader,folder)
#         errors.insert(info)

objs = db.objs
objs.drop()
logger.info("Filling with tests")
leaders = ('te','vt','vm','mo','md','td')
for leader in leaders:
    for folder in os.listdir(os.path.join(REPO_DIR,leader)):
        if folder.startswith("Make"):
            continue
        logger.info("On %s ", folder)
        path = os.path.join(REPO_DIR,leader,folder,"kimspec.ini")
        info = configtojson(path)
        info['kimid'] = folder
        info['path'] = os.path.join(leader,folder)
        objs.insert(info)

