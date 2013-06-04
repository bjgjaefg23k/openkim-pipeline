import pymongo
import os
import yaml
import json
from logger import logging
logger = logging.getLogger('pipeline').getChild('mongofill')

client = pymongo.MongoClient()
db = client.test_database

#tests = db.tests
#tests.insert(post)
REPO_DIR = os.path.abspath("../openkim-repository/")

test_results = db.test_results
test_results.drop()
logger.info("Filling with test results")
for folder in os.listdir(os.path.join(REPO_DIR,"tr/")):
    logger.info("On %s ", folder)
    with open(os.path.join(REPO_DIR,"tr",folder,folder)) as f:
        yaml_docs = yaml.load_all(f)

        info = next(yaml_docs)

        for prop in yaml_docs:
            z = info.copy()
            z.update(prop)
            test_results.insert(z)

from processkimfiles import eatfile
tests = db.tests
tests.drop()
logger.info("Filling with tests")
for folder in os.listdir(os.path.join(REPO_DIR,"te/")):
    logger.info("On %s ", folder)
    test = {}
    test['kimid'] = folder
    test['dotkim'] = eatfile(os.path.join(REPO_DIR,"te",folder,folder+".kim"))
    tests.insert(test)


models = db.models
models.drop()
logger.info("Filling with tests")
for folder in os.listdir(os.path.join(REPO_DIR,"mo/")):
    logger.info("On %s ", folder)
    model = {}
    model['kimid'] = folder
    model['dotkim'] = eatfile(os.path.join(REPO_DIR,"mo",folder,folder+".kim"))
    models.insert(model)

