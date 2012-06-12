#!/bin/bash
rm -r MODEL*
rm -r ~/openkim-repository/md/*
rm -r ~/openkim-repository/mo/*

tar zxvf kim_models_edits.tgz
python rename.py
mv MODEL_DRIVERs/* ~/openkim-repository/md/
mv MODELs/* ~/openkim-repository/mo/
