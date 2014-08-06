OpenKIM Pipeline
===================

Overview
------------

The pipeline is the primary computational resources that are part of the
OpenKIM project.  It is responsible for maintaining the repository of test
results and verification results that are used by researchers to compare and
verify interatomic models.  The pipeline does so by calculating all matches
between Tests (simulation codes) and Models (interatomic models) contained in
the central repository located at ``openkim.org``.  The pipeline is comprised
of many individual machines that work in concert to build and execute a queue
of jobs that are represented by (Test, Model) pairs.

There are three main goals that have driven the decisions in the pipeline:

1. **Provenence** - ability to track the origin of and perfectly recreate every
   test result. This includes control over not only the source for the test and
   model, but the entire software suite including all shared libraries and
   compiler versions

2. **Flexibility** - run on most hardware in many dif- ferent physical locations
   with varying network con- straints.

3. **Ease of development** - utilize standard software packages and protocols
   minimizing the develop- ment and maintenance time.


To this end, the pipeline is built on top of a collection of open source
software with a bit of special sauce binding them together.  In particular, the
pipeline consists of main Gateway machine and a series of Directors and Workers
which all connect to a common queueing system.  When a new result is requested,
the Gateway receives the request and passes it on to the Director.  The
Director calculates which jobs must be performed and sends these jobs to the
Workers for them to compute. The Workers listen for jobs and download the
necessary data from the website's repository, compute and return results.

There are three main ideas that make the pipeline work.  These are:

1. The pipeline source code.  A Python library built to interact over the
   network and run the tests and models.

2. The virtual machine.  Where the code lives and is executed.

3. The network.  How the information is exchanged to make these computations
   happen.

These three parts are described below in varying levels of detail, in reverse
order. Enjoy!

