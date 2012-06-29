Information for developers
==========================


Worker / Director launch
------------------------

.. _initialsetup: 

Initial Setup
^^^^^^^^^^^^^
To create a worker or director you need 2 files and 4 pieces of information.
You need both the approved ``Vagrantfile`` as well as ``secure``, a bash
script which launches the authorization process.  These can be found in
the email where you recieved your authority information.

First, you must install VirtualBox by Oracle and vagrant.  These can be found
at::

    https://www.virtualbox.org/wiki/Downloads
    http://vagrantup.com/

After these are installed, create a new directory (let's call it ``openkim-worker``) and copy the two files
into that directory.  Inside ``openkim-worker``, you need to initialize vagrant using::

    vagrant up

This will download the base box from our central servers (~600MB), unpack, and begin initializing it.
This also begins the provisioning process which will download our latest box configuration 
and download additional software.  During this time, green messages will go flying past on the
screen intermixed with red ones.  Most of the red are related to branch switching in git, however
some are not.  If you find that the provisioning failed, please mail us the output of ``vagrant up`` 
to debug.


Making it Secure
^^^^^^^^^^^^^^^^
After the box is finished upping itself, you need to make it secure by running::

    ./secure

This script will login to the box and launch its authorization measures.  During this time you
will be asked your credentials.  If this process fails, the box will not be secure and
will not become a worker.  Check your credentials again.


Status Monitoring
^^^^^^^^^^^^^^^^^
When this process is complete, you will no longer be able to access the box.  To check on it, there
is a webserver running on the box which gives you the vital signs.  It is port forwarded to the host 
machine at ``14178``.  If you have a browser on that machine you may visit::

    http://127.0.0.1:14178/

to see the status.  If you are on another machine and would like to view this site, you can set
up a port forward using ssh with::

    ssh -L 14178:localhost:14178 user@host 

then again visit the site above.  


Maintenance
^^^^^^^^^^^
Since you are no longer able to access the box via ssh or on the command line, to 
have a notion of maintenance, there is little you can do.  

If the box has gotten out of control and needs to be shutdown, you can attempt to run::

    vagrant halt

which will first try to gracefully halt the machine, then stop it in a less graceful manner.
The method by which it stops is not important, it will come up okay afterward.  You can
also send an ACPI shutdown message from the ``virtualbox`` GUI.

If you would like to entirely reinitialize the box run::

    vagrant destroy

This will make it a fresh start so you need to begin again from :ref:`initialsetup`.


Test development
----------------

Get the box
^^^^^^^^^^^
In order to develop a test for the pipeline, it is highly recommended that you download
and develop on a virtual machine.  This is by far the easiest way to ensure that
your test will be compatible with the pipeline.  To download the box, follow
:ref:`initialsetup`.  After that, you may access the system using::

    vagrant ssh

From here on out, the information is strictly about development, no more virtual machines.


Tests and Test drivers
^^^^^^^^^^^^^^^^^^^^^^
In order to reduce the amount of code reproduction and to ease debug and update, we have
introduced test drivers.  If you intend on making a test which works with multiple options
this is the way to go!  Your test should accept these options on standard input from the 
command line.  From there, you can decide how the test should operate.  

Test drivers
""""""""""""
As a simple example, we wrote a very basic lattice constant test drvier.  It can work for any
species and for any cubic lattice type.  Therefore, are input would look something like
this::

    Please enter the lattice type: <enter fcc, etc>
    Please enter the species: <enter Al, etc>
    Please enter the model: <enter modelname>

These options will provided to your test driver executable at runtime by the pipeline 
based on individual tests that you have created for the test driver.  A test driver 
requires:

1. An executable which accepts any number of stdin inputs and is named the same as the KIM ID and outputs standard json (see :ref:`jsonoutput`)

Yup! that's all it needs.  No ``<KIMID>.kim`` file or anything else.  Of course it can 
have more, but this is all that is required.

Tests
"""""
A test is all of the extra information that is required to run a test driver.  For the example
above, we need to be able to locate our test driver, provide it with a lattice type, species,
and a modelname.  To do this, the tests require 5 files:

1. An executable which accepts input via stdin and is named the same as the KIMID
2. A file called pipeline.in which describes the input to your test
3. A file called pipeline.out which describes the output
4. A <KIMID>.kim file
5. A Makefile (this can be a bare minimum file such as ::

    all:
        @echo "Nothing to make"
    
    clean:
        @echo "Nothing to clean"

After this, you are all set.  Files 2 and 3 are described at :ref:`pipelineindocs` and :ref:`pipelineoutdocs`. 


.. _jsonoutput:

JSON output
^^^^^^^^^^^
We require that the output of your test be a machine readable form called JSON.  This is a standard way to
represent complex objects in ASCII text so that we do not have to create a new standard
of how to print arrays or how to name a scalar.  If you wish to output a binary file, you should check
out the :ref:`pipelineoutdocs` documentation.

There is a library that deals with JSON in almost every language.  For C, it is https://live.gnome.org/JsonGlib,
Python is http://pypi.python.org/pypi/simplejson/, C++ is http://jsoncpp.sourceforge.net/.  Documentation about
the JSON format in general is provided at http://www.json.org/.  

Some brief examples of JSON are here though.  A dictionary of key, value pairs describing a lattice 
constant would look like::

    '{"a0": 3.1415}' 

or an array of numbers that we would like to call the magic numbers is::

    '{"magic_numbers": [4, 42, 163]}'

And the list could go on.

Required Files
^^^^^^^^^^^^^^

.. _pipelineindocs:

pipeline.in
"""""""""""

.. _pipelineoutdocs:

pipeline.out
""""""""""""



Install your test
^^^^^^^^^^^^^^^^^
The working directory for the models and tests is not the standard ``KIM_API/TESTs`` etc.
Instead, we have migrated these to the directory as defined in the environment variable
``KIM_REPOSITORY_DIR`` which has several subdirectories.  You are most concerned with
``te`` and ``td`` which are the tests and test drivers.  

You should copy your test driver to a directory in ``td`` with the same name as your executable,
and copy each of your tests to ``te`` in directories that are named the same as the tests.


Debugging
^^^^^^^^^
After you have installed the tests, you should debug them by trying to run them through the pipeline.
If they require data from another test to complete properly, you need to file it in at this
time as your box will not have a network connection to the secure repository.

You should now attempt to run your test by doing::

    cd /home/vagrant/openkim-pipeline/
    python debugtest.py <testname>

This will attempt to run your test and inform you of any problems that it encountered.  You can
then to debug your test.

.. todo:: create the debugdeveloper.py script which finds all matches and runs them for one test
.. todo:: provide a method to get a sample repository into the boxes to start with

Model development
-----------------
Nothing special needs to be done here.  It works naturally with the KIM API.

