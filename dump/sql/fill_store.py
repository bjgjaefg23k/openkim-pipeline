import sqlite3
from kimobjects import *
import itertools
from ConfigParser import ConfigParser
import os
import yaml
import json


conn = sqlite3.connect('store.db')
c = conn.cursor()

REPO_DIR = "/home/vagrant/openkim-repository/"

objs = itertools.chain(
        Test.all(),
        Model.all(),
        TestDriver.all(),
        ModelDriver.all(),
        VerificationTest.all(),
        VerificationModel.all()
        )

def insert_objs():
    #Insert objects
    for obj in objs:
        c.execute('INSERT INTO object (kimcode,kimid,name,leader,number,version) VALUES (?,?,?,?,?,?);',
                (obj.kim_code,
                obj.kim_code_id,
                obj.kim_code_name,
                obj.kim_code_leader,
                obj.kim_code_number,
                obj.kim_code_version))
        pk = c.lastrowid
        config = ConfigParser()
        config.optionxform = str
        with open(os.path.join(obj.path,'kimspec.ini')) as f:
            config.readfp(f)
        for key,value in config.items('kimspec'):
            c.execute('INSERT INTO object_stuff (object_id,key,value) VALUES (?,?,?)',
                    (pk,key,value))

    conn.commit()

def getpk(kimcode):
    pk, = c.execute('SELECT id FROM object WHERE kimcode = ?',(kimcode,)).fetchone()
    return pk


def insert_matches():
    #Insert the matches
    for te in Test.all():
        print te
        tepk = getpk(te.kim_code)
        for mo in te.models:
            mopk = getpk(mo.kim_code)
            c.execute('INSERT INTO match (runner_id, subject_id) VALUES (?,?)', (tepk, mopk))
    conn.commit()

def flatten_dict(d):
    def items():
        for key, value in d.items():
            if isinstance(value, dict):
                for subkey, subvalue in flatten_dict(value).items():
                    yield key + "." + subkey, subvalue
            elif isinstance(value, list):
                for (pk,item) in enumerate(value):
                    if isinstance(item,dict):
                        for (subkey,subvalue) in flatten_dict(item).items():
                            yield key + ".item{}.".format(pk) + subkey, subvalue
                    else:
                        yield key + ".item{}".format(pk), item
            else:
                yield key, value

    return dict(items())

def insert_trs():
    #insert trs
    trs = [ tr for tr in os.listdir(os.path.join(REPO_DIR,'tr')) if os.path.isdir(os.path.join(REPO_DIR,'tr',tr)) ]
    tot = len(trs)
    for i,tr in enumerate(trs):
        print i,tot,tr
        config = ConfigParser()
        config.optionxform = str
        with open(os.path.join(REPO_DIR,'tr',tr,'kimspec.ini')) as f:
            config.readfp(f)
            info = dict(config.items('kimspec'))
            tepk = getpk(info['TEST_NAME'])
            mopk = getpk(info['MODEL_NAME'])

        #insert into results
        c.execute('INSERT INTO result (runner_id, subject_id, uuid, kind) VALUES (?,?,?,"tr")',
                (tepk, mopk, tr))
        trid = c.lastrowid

        #process yamls
        with open(os.path.join(REPO_DIR,'tr',tr,'results.yaml')) as f:
            docs = yaml.load_all(f)

            for doc in docs:
                c.execute('INSERT INTO property (name,blob) VALUES (?,?)',
                        (doc['kim-template-tags'][0], json.dumps(doc)))
                prid = c.lastrowid
                c.execute('INSERT INTO result_property (result_id, property_id) VALUES (?,?)',
                        (trid, prid))

                flatdoc = flatten_dict(doc)
                for key,value in flatdoc.iteritems():
                    c.execute('INSERT INTO property_stuff (property_id, key, value) VALUES (?,?,?)',
                        (prid, key, value))

    conn.commit()


def insert_vrs():
    #insert trs
    vrs = [ vr for vr in os.listdir(os.path.join(REPO_DIR,'vr')) if os.path.isdir(os.path.join(REPO_DIR,'vr',vr)) ]
    tot = len(vrs)
    for i,vr in enumerate(vrs):
        print i,tot,vr
        config = ConfigParser()
        config.optionxform = str
        with open(os.path.join(REPO_DIR,'vr',vr,'kimspec.ini')) as f:
            config.readfp(f)
            info = dict(config.items('kimspec'))
            try:
                runner = info['VERIFICATION_TEST']
            except:
                runner = info['VERIFICATION_MODEL']
            try:
                subject = info['TEST_NAME']
            except:
                subject = info['MODEL_NAME']
            runnerpk = getpk(runner)
            subjectpk = getpk(subject)

        #insert into results
        c.execute('INSERT INTO result (runner_id, subject_id, uuid, kind) VALUES (?,?,?,"vr")',
                (runnerpk, subjectpk, vr))
        vrid = c.lastrowid

        try:
            #process yamls
            with open(os.path.join(REPO_DIR,'vr',vr,'results.yaml')) as f:
                docs = yaml.load_all(f)

                for doc in docs:
                    c.execute('INSERT INTO property (name,blob) VALUES (?,?)',
                            (doc['kim-template-tags'][0], json.dumps(doc)))
                    prid = c.lastrowid
                    c.execute('INSERT INTO result_property (result_id, property_id) VALUES (?,?)',
                            (vrid, prid))

                    flatdoc = flatten_dict(doc)
                    for key,value in flatdoc.iteritems():
                        c.execute('INSERT INTO property_stuff (property_id, key, value) VALUES (?,?,?)',
                            (prid, key, value))
        except:
            print "ERROR ON ", vr

    conn.commit()

def insert_ers():
    #insert trs
    ers = [ er for er in os.listdir(os.path.join(REPO_DIR,'er')) if os.path.isdir(os.path.join(REPO_DIR,'er',er)) ]
    tot = len(ers)
    for i,er in enumerate(ers):
        print i,tot,er
        config = ConfigParser()
        config.optionxform = str
        with open(os.path.join(REPO_DIR,'er',er,'kimspec.ini')) as f:
            config.readfp(f)
            info = dict(config.items('kimspec'))
            tepk = getpk(info['TEST_NAME'])
            mopk = getpk(info['MODEL_NAME'])

        #insert into results
        c.execute('INSERT INTO result (runner_id, subject_id, uuid, kind) VALUES (?,?,?,"er")',
                (tepk, mopk, er))
        erid = c.lastrowid

    conn.commit()

