Code
====

Overview of major files
-------------------------

Pipeline
^^^^^^^^^^^
This is the file that is actually run when launching a director or worker.  You can start it
with either::

    python pipeline.py director

or::

    python pipeline.py worker

and it will begin the process of connecting and running jobs. The overall flow of the pipeline
worker is:

1. Create an ssh tunnel, port forwarding the beanstalkd port to the site machine
2. Connect to the beanstalkd
3. Wait for the jobs to roll in!
4. When we get one, rsync the appropriate files as listed in the message
5. Run the test, model pair
6. Rsync the results back to the repo
7. Repeat from 3.

The work flow of the director is slightly different

1. Create an ssh tunnel with the port forward
2. Connect to beanstalkd.
3. Listen for updated tests/models from the website
4. Resolve the dependencies for the udpate.  If these exist, put them on the queue
5. Put the original job on the queue with a list of required files to grab
6. Wait for results back.
7. Repeat from 3.

These are wrapped in an infinite and run as a daemon process at init.d after networking comes up.


rsync Tools
^^^^^^^^^^^^^^
These are a series of wrappers to the ``rsync`` linux command which copies files across
a network.  

.. todo:: Set this up for port forwarding 


Runner
^^^^^^
This is where the magic happens.  Finally, a test is run using the ``pipeline.in.tmp`` stdin
file.  Errors are caught as necessary, otherwise the last line is grabbed as the json string
of output.


Template
^^^^^^^^^
This the Python module which handles dependencies and templating for the pipeline.in file.  
Most tests are not going to be as simple as simply running.  For example, a test will always
at least need to know what the modelname is that it should run.  Therefore, we have created a simple
templating engine that accepts some basic inputs.  These should be placed in a file called ``pipeline.in``
and can contain the following::

    @PATH[KIM_ID] -- returns the path to a kimid object in the repository
    @FILE[./relative/path/to/file] -- will ensure that this file is copied back as a result
    @MODELNAME -- fills in the modelname
    @DATA[TR_ID][TEST_ID][MODEL_ID] -- will return previously computed data

Before a test is submitted by the director, the ``@DATA`` directive is used to find
dependencies of this test.  These are then resolved if they don't exist.  The other directives are
filled in and the file passed to the test executable as a pipe (since all languages support stdin).



Models
^^^^^^
This is a Python abstraction of the Tests, Models, TestDrivers, ModelDrivers, TestResults... etc.  
They have most of the methods that one would feel are natural to ask of the object.  For example,
a test knows its testdriver, which results it produced and key metadata about itself.  


Source code
-----------
Below is some detailed descriptions of the code itself

.. toctree::
    
    codedocs/config
    codedocs/models
    codedocs/pipeline
    codedocs/runner
    codedocs/kimapi
    codedocs/database
    codedocs/rsync_tools
    codedocs/template
    codedocs/persistentdict

