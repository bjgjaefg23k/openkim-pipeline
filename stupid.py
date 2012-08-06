#! /usr/bin/env python

from models import *
from runner import *


test = Test("LatticeConstantCubicStress_Fe_fcc__TE_582286276604_000")
# model = Model("TB_Khakshouri_F_Fe__MO_853979044095_000")
mlist = list(test.models)

# import kimapi
# print kimapi.valid_match(test,model)
