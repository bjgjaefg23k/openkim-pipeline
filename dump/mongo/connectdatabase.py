import pymongo
import os
import yaml
import json
from logger import logging
logger = logging.getLogger('pipeline').getChild('connect')

client = pymongo.MongoClient()
db = client.database
objs = db.objs
results = db.results
errors = db.errors
verifications = db.verifications

