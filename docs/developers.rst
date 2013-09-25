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

.. _testdev:

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

(specific tutorials can be found in :doc:`tutorial_ase` and :doc:`tutorial_lammps`.)

In order to reduce the amount of code reproduction and to ease debug and update, we have
introduced test drivers.  If you intend on making a test which works with multiple options
this is the way to go!  Your test should accept these options on standard input from the 
command line.  From there, you can decide how the test should operate.  

Test drivers
""""""""""""
As a simple example, we wrote a very basic lattice constant test drvier.  It can work for any
species and for any cubic lattice type.  Therefore, our input would look something like
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

.. _desctests:

Tests
"""""
A test is all of the extra information that is required to run a test driver.  For the example
above, we need to be able to locate our test driver, provide it with a lattice type, species,
and a modelname.  To do this, the tests require 5 files:

1. An executable which accepts input via stdin and is named the same as the KIMID
2. A file called pipeline.stdin which describes the input to your test
3. A file called pipeline.yaml which is a jinja template of the results YAML document
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
We require that the output of your test be a machine readable form called JSON printed as 
last line of your program (new newlines, carriage returns, etc).  This is a standard way to
represent complex objects in ASCII text so that we do not have to create a new standard
of how to print arrays or how to name a scalar.  If you wish to output a binary file, you should check
out the :ref:`pipelineoutdocs` documentation.

There is a library that deals with JSON in almost every language.  For C, it is https://live.gnome.org/JsonGlib,
Python is http://pypi.python.org/pypi/simplejson/, C++ is http://jsoncpp.sourceforge.net/, 
Fortran 95 is https://github.com/josephalevin/fson.  
Documentation about the JSON format in general is provided at http://www.json.org/.  

Some brief examples of JSON are here though.  A dictionary of key, value pairs describing a lattice 
constant would look like::

    {"a0": 3.1415} 

or an array of numbers that we would like to call the magic numbers is::

    {"magic_numbers": [4, 42, 163]}

And the list could go on.

Addtionally, if you wish to store binary data you can have as your output, save
a file to the ``output`` directory inside the test directory.  You do not need
to create this folder, it will be created by the pipeline upon invoking a run.  

Required Files
^^^^^^^^^^^^^^
In order to recieve input from the pipeline to run your test, there is a
specific form that you should expect input.  In particular, there are two new
files that you need to provide along with your output in JSON. 


.. _pipelineindocs:

pipeline.stdin.tpl
"""""""""""""""""""

The ``pipeline.stdin.tpl`` file will be passed to your test on standard input upon
its executation by the pipeline.  You should ensure that your test works in
this way.

Before being passed to the test, the ``pipeline.stdin.tpl`` will be templated using 
the same jinja environment used to translate ``results.yaml.tpl`` into proper test
results.  In the environment, there are other pieces of information and 
functions available that you can utilize which will be filled in at runtime.
These are written in proper Python syntax.

The templating environment has several functions and variables available on path
 * path(kim_code)
    This directive will be replaced by the path to the kim code you've given.
    If the object is executable (i.e. a test or test driver) the path given
    will be to its executable, otherwise the path is to the folder the kim
    object lives in. For example, if you're test derives from a TestDriver, you
    will need to reference it's executable and pass in the necessary inputs for
    it to run, if you wanted the executable for test driver
    ``TD_000000000001_000`` you would put::
        
        path(TD_000000000001_000)

    at the top of your ``pipeline.stdin.tpl`` file.  Like most things requesting KIM
    codes, you are allowed to put partial KIM codes (i.e. leaving out the name
    or the version number or both), leaving out the version number will get you
    the latest version in the repository

 * MODELNAME
    This one is required, and it will be replaced by the full kim name of the
    model your test is being run against.  Use this to invoke the KIM_API_init
    for the model you're running against

 * query(query_object)
    The query function is used to request data from the database. Examples for
    how to use this function are provided on the query page 
    `here <https://query.openkim.org>`_.

    It is recommended that you take advantage of the ``project`` mechanism
    in your query so that the query will return a bare number for usage in
    the test.

.. _pipelineoutdocs:

results.yaml.tpl
""""""""""""""""
This file is a template for the YAML file that will be reported as the
official test result.  The basis for this file comes from the main 
`KIM site <https://portal.openkim.org>`_ and is composed of properties and primitives
that describe the test results.  In this file, each value you want to report should
be replaced with a templating directive where the key matches the JSON output
of your test.  

For example, if you wanted to report a cohesive energy, the primitive in this file
would look like this::

    energy:
        kim-namespace:  tag:staff@noreply.openkim.org,2013-08-03:primitive/cohesive-energy
        source-value: @<cohesive_energy>@
        source-unit:  eV

In the JSON output of the test, the key ``cohesive_energy`` should be reported.  Upon
completion, this value will be filled in by the pipeline.

A brief example
^^^^^^^^^^^^^^^
Let's pretend we have an executable that computes the energy of a cluster of atoms given
by a configuration file that lives with the executable.  The test driver is called
``energy__TD_000000000000_000`` because we were able to secure a special KIM code for 
this exercise.  In the directory ``td/energy__TD_000000000000_000``, we have the files::

    > ls -l energy__TD_000000000000_000
    rw-r--r-- 1 openkim openkim configuration.dat
    rwxr--r-- 1 openkim openkim energy__TD_000000000000_000

The executable takes a number of command line arguments.  In particular, when it is 
run, the user is prompted for the following information::

    > ./energy__TD_000000000000_000
    Please enter the species: Ar
    Please enter the modelname: ex_model_Ar_P_LJ

After this is entered, it loads the configuration file and calculates the energy.  As 
specified above, the last line of the output is a JSON string which is a dictionary
of output names and their values.  The full output of our sample program looks like 
this::

    Calculating energy of Ar atoms using ex_model_Ar_P_LJ using configuration.dat...
    Loading configuration...
    Successful completion, saving
    {"total_energy": -1.9711}

Notice the last line again is JSON, but all of the other lines can be whatever you please.

Now, the problem is: "How does our test driver get a species with which to run?"  We need to
create a test that knows these sorts of things.  We will name it in relation to our
base test driver and call it ``energyAr__TE_000000000000_000``.  Again, the KIM code we
recieved for our test is quite special.  This test is very simple, it will run the test driver
and provide the option ``Ar`` where appropriate.  We need 5 files for our test, they are::

    > ls te/energyAr__TE_000000000000_000   
    energyAr__TE_000000000000_000 energyAr__TE_000000000000_000.kim Makefile
    pipeline.stdin pipeline.yaml

The contents of ``pipeline.stdin`` are::

    @PATH[energy__TD_000000000000_000]
    Ar
    @MODELNAME

The first line is going to be parsed by the pipeline so we can find the path of
our test driver executable in the pipeline system.  The second two lines are in
response to the test drivers questions.  Again, ``@MODLENAME`` is filled in by
the pipeline when it is run.  The file ``pipeline.yaml`` contains the properties
and primitives that have been approved to represent your test output.

The .kim file specifies what requirements your test driver has
when run with these arguments, it won't be listed here.  The ``Makefile`` can
be as blank as possible (see :ref:`desctests`) as we will be using a Python
script as our main executable and it doesn't need to be made.  Finally, our
Python script runs the path as returned by the ``@PATH`` directive and then
simply passes along stdin input to our test driver.  The contents of this file
are::

    #!/usr/bin/env python 
    import sys
    from subprocess import Popen, PIPE
    from StringIO import StringIO
    import fileinput
    
    inp = fileinput.input()
    exe = next(inp).strip()
    args = "".join([line for line in inp])
    
    try:
        proc = Popen(exe, stdin=PIPE, stdout=sys.stdout,
                    stderr=sys.stderr, shell=True)
        proc.communicate(input=args)
    except Exception as e:
        pass
    finally:
        exit(proc.returncode)

There we have our simple test.  If we wanted to make more tests, we would need
to change the name of folder, executable, and kim file.  Then we could change
the species name in ``pipeline.stdin``. 
 

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

    pipeline_verify <testname>
    pipeline_runmatches <testname>

This will attempt to run your test and inform you of any problems that it encountered.  You can
then to debug your test.

.. todo:: create the debugdeveloper.py script which finds all matches and runs them for one test
.. todo:: provide a method to get a sample repository into the boxes to start with

Model development
-----------------
Nothing special needs to be done here.  It works naturally with the KIM API.

