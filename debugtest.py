#!/usr/bin/env python
import models
import runner
import sys

if __name__ == "__main__":
    if len(sys.argv) == 2:
        testname = sys.argv[1]
        test = models.Test(testname)
        if len(list(test.models)) > 0:
            for model in test.models:
                print "Running combination <%r, %r" % (test, model)
                runner.run_test_on_model(test, model)
        else:
            print "No matches found for your test"
    else:
        print "Usage: debugtest.py <testname>"
