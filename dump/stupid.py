
from kimobjects import *

te = Test('LatticeConstantCubicEnergy_Fe_fcc__TE_142821659808_000')
mo = Model('TB_FinnisSinclair_F_Fe__MO_641218889561_000')

from compute import Computation
c = Computation(te,mo)

trid = "TR_000000000001_001"


