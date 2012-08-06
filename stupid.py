#! /usr/bin/env python

from models import *
from runner import *


test = Test("LatticeConstantEnergy_Fe_fcc__TE_248695510051_000")
model = Model("TB_Khakshouri_F_Fe__MO_853979044095_000")

import kimapi
print kimapi.valid_match(test,model)
