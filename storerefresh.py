#! /usr/bin/env python
""" This file is meant to refresh the stores if we ever get out of sync """

import kimid
from persistentdict import PersistentDict, PersistentDefaultDict
from config import *
import repository as repo

allkimids = []
for dir in KIM_REPO_DIRS:
    for kimid in (subdir for subdir in os.listdir(dir) if os.path.isdir(subdir)):
        allkimids.append(kimid)

#try to populate all of the kimids
with PersistentDefaultDict(KIMID_STORE) as store:
    for kimid in allkimids:
        leader,pk,version = kimid.parse_kimid(kimid)
        
        substore = store[leader]
        if pk in store[leader]:
            if version > store[leader][pk]:
                store[leader][pk] = version
        else:
            store[leader][pk] = version

#try to populate the prediction store
with PersistentDefaultDict(PREDICTION_STORE) as store:
    for pred in os.listdir(KIM_PREDICTIONS_DIR):
        info = repo.load_info_file(os.path.join(KIM_PREDICTIONS_DIR,pred,pred))
        testname = info["_testname"]
        modelname = info["_modelname"]
        store[testname][modelname] = pred




