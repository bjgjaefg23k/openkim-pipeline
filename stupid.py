#! /usr/bin/env python
from repository import *

test = 'TE_333333333333_000'
model = 'MO_607867530928_000'

guy = ("LatticeConstantCubicFccAl__TE_000000000159_000",'IMD_AlMnPd__MO_265192693592_000')

foo = valid_match(*guy, force=True)
print foo
