from repository import *

model = KIM_MODELS[2]
tests = list(tests_for_model(model))

print tests


import runner
foo = runner.run_test_on_model(tests[2],model)
print foo
