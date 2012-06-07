#!/bin/bash
REPO=~/openkim-repository
HERE=`pwd`

# remove the old models and tests
cd $REPO
git rm -r ./te/*
git rm -r ./mo/*
cd $HERE

mkdir -p $REPO/mo/
mkdir -p $REPO/te/

tar zxvf FullLJ.tgz
python make_models.py
mv MO_* $REPO/mo/

python make_lattice_tests.py
mv TE_0* $REPO/te/

python make_elastics_tests.py
mv TE_2* $REPO/te/

python make_surface_tests.py
mv TE_1* $REPO/te/

