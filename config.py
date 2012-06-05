""" 
Holds all of the GLOBAL configuration variables 

"""

import os

#==============================
# KIM FLAGS
#===============================

#get the kim directories
KIM_DIR = os.environ["KIM_DIR"]
KIM_API_DIR = os.environ.get("KIM_API_DIR",
        os.path.join(KIM_DIR,"KIM_API"))
#KIM_MODELS_DIR = os.environ.get("KIM_MODELS_DIR",
#        os.path.join(KIM_DIR,"MODELs"))
#KIM_MODEL_DRIVERS_DIR = os.environ.get("KIM_MODEL_DRIVERS_DIR",
#        os.path.join(KIM_DIR,"MODEL_DRIVERs"))
#KIM_TESTS_DIR = os.environ.get("KIM_TESTS_DIR",
#        os.path.join(KIM_DIR,"TESTs"))
#KIM_TEST_DRIVERS_DIR = os.environ.get("KIM_TEST_DRIVERS_DIR",
#        os.path.join(KIM_DIR,"TEST_DRIVERs"))

#get the repository dir from the symlink
KIM_REPOSITORY_DIR = os.readlink('openkim-repository')

PIPELINE_INFO_FILE = "pipelineinfo.json"


#===========================
# Directory codes
#===========================

KIM_PREDICTIONS_DIR = os.path.join(KIM_REPOSITORY_DIR,"pr")
KIM_REFERENCE_DATA_DIR = os.path.join(KIM_REPOSITORY_DIR,"rd")
KIM_MODELS_DIR = os.path.join(KIM_REPOSITORY_DIR,"mo")
KIM_MODEL_DRIVERS_DIR = os.path.join(KIM_REPOSITORY_DIR,"md")
KIM_TEST_DIR = os.path.join(KIM_REPOSITORY_DIR,"te")
KIM_TEST_DRIVERS_DIR = os.path.join(KIM_REPOSITORY_DIR,"td")

#get all of the models
KIM_MODELS = [ dir for dir in os.listdir(KIM_MODELS_DIR) if os.path.isdir(os.path.join(KIM_MODELS_DIR,dir)) ]
#and all of the tests
KIM_TESTS =  [ dir for dir in os.listdir(KIM_TESTS_DIR) if os.path.isdir(os.path.join(KIM_TESTS_DIR,dir)) ]
KIM_TEST_DRIVERS = [ dir for dir in os.listdir(KIM_TEST_DRIVERS_DIR) if os.path.isdir(os.path.join(KIM_TEST_DRIVERS_DIR,dir))]
KIM_MODEL_DRIVERS = [dir for for in os.listdir(KIM_MODEL_DRIVERS_DIR) if os.path.isdir(os.path.join(KIM_MODEL_DRIVERS_DIR,dir))]


#============================
# Settings for remote access
#============================

GLOBAL_IP   = "127.0.0.1"
GLOBAL_PORT = 14177

GLOBAL_USER = "sethnagroup"
GLOBAL_HOST = "cerbo.ccmr.cornell.edu"
GLOBAL_DIR  = "/home/sethnagroup/vagrant/openkim-repository/"


#============================
# Stores
#============================

