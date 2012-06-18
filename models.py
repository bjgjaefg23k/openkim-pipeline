""" Here is where all of the relational database models should live """

from config import *
import sqlalchemy as sql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, Text
from sqlalchemy.orm import relationship, backref, sessionmaker
import datetime

engine = sql.create_engine("sqlite:////home/vagrant/openkim-repository/test.db", echo=True)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

import re
RE_KIMID    = r"(?:([_a-zA-Z][_a-zA-Z0-9]*)?_?_)?([A-Z]{2})_([0-9]{12})(?:_([0-9]{3}))?"


#Base.metadata.create_all(engine)


class KIMObject(Base):
    """ The base KIMObject """
    __tablename__ = "kim_objects"

    #primary key
    id = Column(Integer, primary_key=True)
    #path to folder
    path = Column(String)

    #kim code stuff
    kim_code = Column(String)
    kim_code_name = Column(String, nullable=True)
    kim_code_leader = Column(String(length=2))
    kim_code_number = Column(String(length=12))
    kim_code_version = Column(String(length=3))

    #created on
    created_on = Column(DateTime, default=datetime.datetime.now)

    def __init__(self,kim_code):
        #given a kim_code try to break it down 
        name, leader, num, version = re.match(RE_KIMID,kim_code).groups() 
        #set to zero if not given
        version = version or '000'

        #save attributes
        self.kim_code_name = name
        self.kim_code_leader = leader
        self.kim_code_number = num
        self.kim_code_version = version
        if name:
            self.kim_code = "{}__{}_{}_{}".format(name,leader,num,version)
        else:
            self.kim_code = "{}_{}_{}".format(leader,num,version)
        self.path = os.path.join(KIM_REPOSITORY_DIR,leader.lower(),self.kim_code) 

    def __repr__(self):
        return "<KIMObject({})>".format(self.kim_code)


# association table for tests and properties
test_properties = Table('test_properties', Base.metadata,
        Column('test_id', Integer, ForeignKey('tests.id')),
        Column('property_id', Integer, ForeignKey('properties.id')))

class Property(Base):
    """ A property """
    __tablename__ = "properties"
    #primary key
    id = Column(Integer, primary_key=True)
    info = Column(Integer,ForeignKey('kim_objects.id'))
    # a property has many reference data
    reference_data = relationship("ReferenceDatum",backref="property")
    labels = Column(Text,nullable=True)

class Test(Base):
    """ A KIM Test """
    __tablename__ = "tests"
    #primary key
    id = Column(Integer, primary_key=True)
    info = Column(Integer,ForeignKey('kim_objects.id'))

    # a test has many properties (Many to many)
    properties = relationship("Property",secondary=test_properties,backref="tests")
    # a test has many results
    results = relationship("TestResult",backref="test")
    # a test may have a test driver
    test_driver_id = Column(Integer, ForeignKey("test_drivers.id"), nullable=True)


class Model(Base):
    """ A KIM MODEL """
    __tablename__ = "models"
    #primary key
    id = Column(Integer, primary_key=True)
    info = Column(Integer,ForeignKey('kim_objects.id'))

    #a model has many results
    results = relationship("TestResult",backref="model")
    # a model has many VCs
    verification_results = relationship("VerificationResult",backref="model")
    # a model may have a model driver
    model_driver_id = Column(Integer,ForeignKey("model_drivers.id"),nullable=True)


class TestResult(Base):
    """ A test result """
    __tablename__ = "test_results"
    #primary key
    id = Column(Integer, primary_key=True)
    info = Column(Integer,ForeignKey('kim_objects.id'))

    # a test result has a test
    test_id = Column(Integer,ForeignKey('tests.id'))
    # a test result has a model
    model_id = Column(Integer,ForeignKey('models.id'))
    


class ModelDriver(Base):
    """ A model driver """
    __tablename__ = "model_drivers"
    #primary key
    id = Column(Integer, primary_key=True)
    info = Column(Integer,ForeignKey('kim_objects.id'))

    # a model driver has many models
    models = relationship("Model",backref="model_driver")


class TestDriver(Base):
    """ A test driver """
    __tablename__ = "test_drivers"
    #primary key
    id = Column(Integer, primary_key=True)
    info = Column(Integer,ForeignKey('kim_objects.id'))

    # a test driver has many tests
    tests = relationship("Test",backref="test_driver")


class VerificationCheck(Base):
    """ A verification check """
    __tablename__ = "verification_checks"
    #primary key
    id = Column(Integer, primary_key=True)
    info = Column(Integer,ForeignKey('kim_objects.id'))

    # a verification check has many results
    verification_results = relationship("VerificationResult", backref="verification_check")

class VerificationResult(Base):
    """ A verification result """
    __tablename__ = "verification_results"
    #primary key
    id = Column(Integer, primary_key=True)
    info = Column(Integer,ForeignKey('kim_objects.id'))

    # a VR has a VC
    verification_check_id = Column(Integer,ForeignKey('verification_checks.id'))
    # A VR has a model 
    model_id = Column(Integer,ForeignKey('models.id'))


class ReferenceDatum(Base):
    """ Some reference data """
    __tablename__ = "reference_data"
    #primary key
    id = Column(Integer, primary_key=True)
    info = Column(Integer,ForeignKey('kim_objects.id'))

    # reference data references a property
    property_id = Column(Integer,ForeignKey("properties.id"))

class VirtualMachine(Base):
    """ Virtual Machine """
    __tablename__ = "virtual_machines"
    #primary key
    id = Column(Integer, primary_key=True)
    info = Column(Integer,ForeignKey('kim_objects.id'))



