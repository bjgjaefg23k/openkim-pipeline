#! /usr/bin/env python

from models import *
from runner import *

tr = TestResult("TR_117687325786_000")
test = tr.test
model = tr.model


import kimapi
print kimapi.valid_match(test,model)
