OpenKIM Pipeline
===================

Overview
------------
The pipeline consists of a number of parts that need to work closely together.

There is a central website which hosts ``openkim.org`` and stores the repository
of models, tests, and results for browsing and download by members of KIM.
It also has review processes to accept new models and tests and is the central
front end hub of the OpenKIM project.

The pipeline is the backend which computes the results of tests, models, and
verifications to generate data for the website.  The website notifies the
pipeline what it would like to have computed and the pipeline figures out
how to make it so. 

In particular, the pipeline consists of a series of directors and workers which
all connect to a common queueing system.  Here, the director gets pings from
the website that computations must be completed, and the director sends out
jobs to the workers for them to compute.  The workers listen for jobs and 
download the necessary data from the website's repository, compute and return 
results.  

There are three main ideas that make the pipeline work.  These are:

1. The pipeline source code.  A Python library built to interact over the network and run the tests and models.
2. The virtual machine.  Where the code lives and is executed.
3. The network.  How the information is exchanged to make these computations happen.

These three parts are described below in varying levels of detail, in reverse order. Enjoy!


