#! /usr/bin/env python
from repository import *

test = 'TE_333333333333_000'
model = 'MO_607867530928_000'

guy = ('TE_000000000014_000','MO_607867530916_000')

import runner
foo = valid_match(*guy)
print foo
