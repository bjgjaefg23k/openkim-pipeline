#!/usr/bin/env python
import database
import models
import runner
import sys

if __name__ == "__main__":
    if len(sys.argv) == 2:
        testname = sys.argv[1]
        name,leader,num,version = database.parse_kim_code(testname)
        if leader == "TE":
            test = models.Test(testname)
            if len(list(test.models)) > 0:
                for model in test.models:
                    print "Running combination <%r, %r" % (test, model)
                    runner.run_test_on_model(test, model)
            else:
                print "No matches found for your test"
        else:
            test = models.TestDriver(testname)
            if len(list(test.tests)) > 0:
                for t in test.tests:
                    for m in t.models:
                        print "Running combination <%r, %r" % (t, m)
                        runner.run_test_on_model(t, m)
            else:
                print "No matches found for your test"
    
    else:
        print "Usage: debugtest.py <testname>"