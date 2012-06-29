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

.. toctree::
   :maxdepth: 3

   pipeline
   network
   virtualbox
   developers
   code

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


ToDos
=====

.. todolist::
