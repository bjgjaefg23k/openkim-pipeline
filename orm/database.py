""" Set up the database, engine and session """

from config import *
import sqlalchemy as sql

engine = sql.create_engine("sqlite:///test.db", echo=True)

Base = sql.ext.declarative.declarative_base()


