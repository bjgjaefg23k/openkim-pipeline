#!/bin/bash
REPO=~/openkim-repository
HERE=`pwd`

# remove the old models and tests
cd $REPO
git commit -a -m "storing what you have"
git rm -r ./te/*
git rm -r ./mo/*
git rm -r ./md/*
git rm -r ./td/*
cd $HERE

mkdir -p $REPO/mo/
mkdir -p $REPO/te/
mkdir -p $REPO/td/
mkdir -p $REPO/md/

tar zxvf FullLJ.tgz
python make_models.py
mv MO_* $REPO/mo/

python make_lattice_tests.py
mv TE_0* $REPO/te/

python make_elastics_tests.py
mv TE_2* $REPO/te/

python make_surface_tests.py
mv TE_1* $REPO/te/

cp -r test_drivers/* $REPO/td/
cp -r model_drivers/* $REPO/md/
cp -r test_singles/* $REPO/te/
cp -r model_singles/* $REPO/mo/

cd $REPO
cd te; for i in `ls`; do chmod +x $i/$i; done; cd ..
cd td; for i in `ls`; do chmod +x $i/$i; done; cd ..
cd $HERE

cd $KIM_DIR
make
cd $HERE

cd $REPO
git add .
git commit -m "done building"
cd $HERE
