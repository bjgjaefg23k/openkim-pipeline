.. OpenKIM Pipeline documentation master file, created by
   sphinx-quickstart on Thu Jun 28 10:17:31 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to OpenKIM Pipeline's documentation!
============================================
The OpenKIM pipeline is the backbone of the computational resources that the KIM 
project will use.  The goal is to provide a reliable provenance for the computational
results that are central to the goals of KIM.  The pipeline will run verification checks
and tests for every model in order to best compare and understand the uses of 
interatomic models.  The results of these tests must be reproducable and their origins
trusted so that it may become a resource to the scientific community.  

In order to do so, we have designed a system that relies on many standard software packages
that allow us to abstract locations and hardware to provide standard computational resources
that have very little overhead to instantiate.  The key ingredients to the project are listed
below.

FAQS
----

 * How do I write tests that comply with the pipeline?
    Look in the `Test Development <developers.html#test-development>`_ section of :doc:`developers`

 * How do I download a virtual box?
    Look in the `Initial Setup <developers.html#initial-setup>`_ section of :doc:`developers`

 * How do I create a worker?
    Look in the `Initial Setup <developers.html#worker-director-launch>`_ section of :doc:`developers`, again

 * How do the virtual boxes all stay synced?
    See :doc:`virtualbox`

 * What sort of network connections need to exist for this all to work?
    See :doc:`network`

 * How does the pipeline work?
    See :doc:`pipeline`

 * How do I play around with the database on my machine?
    See :doc:`orm`
    
 * How did you get all of this to work?
    Good question! You could read all the gory details in :doc:`code`

Table of Contents
=================

.. toctree::
   :maxdepth: 3

   pipeline
   network
   beanstalkd
   virtualbox
   developers
   orm
   code

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


ToDos
=====

.. todolist::
