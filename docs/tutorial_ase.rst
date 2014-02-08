Example test - ASE
==================

Here, we describe a very basic test using the Atomic Simulation Environment
(ASE) and Python binding for the OpenKIM API.  In this test, we gather the Ar
body center cubic lattice constant from the OpenKIM database.  Using this
lattice constant, we set up a single atom unit cell and calculate it's energy,
reporting it as the cohesive energy.  For a general overview on test format,
have a look at the documentation for :ref:`desctests`.  

For this example, we have adopted the descriptive KIM short name of
ASECohesiveEnergyFromQuery_fcc_Ar and have been provided with the KIM code
TE_102111117114_000.  

.. _ase_listoffiles: 

List of files
-------------

Along with a ``LICENSE`` file and ``README``, we have the six files that are
required to be a valid KIM test in the repository.  We will step through each
of them in order to build our test:

    * :ref:`aseref_exec` - the main executable, a Python script
    * :ref:`aseref_kimfile` - our KIM file which describes our capability
    * :ref:`aseref_kimspec` - file that describes our test meta-data
    * :ref:`aseref_makefile` - a Makefile
    * :ref:`aseref_stdin` - a Jinja template file to provide input on stdin
    * :ref:`aseref_results` - a Jinja template file for the results
    * ``README.md`` - a basic explanation of the test
    * ``LICENSE.CDDL`` - a copy of the standard license

.. _aseref_exec:

ASECohesiveEnergyFromQuery_fcc_Ar__TE_102111117114_000
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is the standalone Python script that takes as input a model name
and lattice constant and calculates the energy at that constant.

The script is short enough that we should take a look at it here::

    #!/usr/bin/env python
    """
    ASE cohesive energy example test
    
    Date: 2013/09/20
    Author: Matt Bierbaum
    """
    from ase.structure import bulk
    from kimcalculator import KIMCalculator
    import json
    
    #grab from stdin (or a file)
    model = raw_input("modelname=")
    lattice_constant = raw_input("lattice constant=")
    lattice_constant = 10**10 * float(lattice_constant)
    
    # calculate the cohesive energy
    calc = KIMCalculator(model)
    slab = bulk('Ar', 'fcc', a=lattice_constant)
    slab.set_calculator(calc)
    energy = -slab.get_potential_energy()
    
    # pack the results in a dictionary
    results = {'lattice_constant': lattice_constant,
                'cohesive_energy': energy}
    
    #print json output
    print "\n", json.dumps(results)


It begins by grabbing the model name and lattice constant from standard input.
The test assumes that the lattice constant will be input in SI units, so we
convert it to angstroms and make sure it's a float.   Next, we initialize an
ASE calculator that integrates with KIM using the model name that was provided.
We set up a single atom unit cell of fcc Ar with the given lattice constant,
and ask for the potential energy.  Finally, we pack the results into a dictionary
which we output in JSON format to stdout.  This output will be used to supplement
the standard Jinja templating environment when filling in the blanks for the
file :ref:`aseref_results`.

.. _aseref_kimfile:

ASECohesiveEnergyFromQuery_fcc_Ar__TE_102111117114_000.kim
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is our KIM file as specified by the standards of the KIM project.  
In this file we limit our neighbor locator methods to ``RVEC_F`` since we
employ a parallelpiped boundary cell with only one atom. 

.. _aseref_kimspec:

kimspec.yaml
^^^^^^^^^^^^

This file contains meta-data which makes it a valid KIM test in the
OpenKIM repository.  In our case, it look like::

    title: ASE cohesive energy test example
    test-driver: 
    species: Ar
    extended-id: ASECohesiveEnergyFromQuery_fcc_Ar__TE_102111117114_000
    disclaimer: Tutorial test using the Atomic Simulation Environment which calculates the cohesive energy
    domain: openkim.org

For more information about these fields, you can look at 
`kimspec.yaml docs <https://kim-items.openkim.org/kimspec-format>`_.

.. _aseref_makefile:

Makefile
^^^^^^^^

Since this is a Python script, we include a phony ``Makefile`` with the contents::

    all:
        @echo "Nothing to make"
    
    clean:
        @echo "Nothing to clean"

.. _aseref_stdin: 

pipeline.stdin.tpl
^^^^^^^^^^^^^^^^^^

This is a template file that the pipeline will fill in and provide to the test
on standard input.  Since we have two items that we would like (model name and
lattice constant) then there are two lines in our stdin file.  In the Jinja
environment, we have chosen ``@[...]@`` to denote a code block, ``@<...>@`` to
denote a variable, and ``@#...#@`` a comment.  In between these braces, Jinja
executes whatever it finds as Python code.  Many standard functions are
available as well as a set of specialty functions that we have defined as part
of the pipeline.  You can find a description of them here :ref:`pipelineindocs`.

Let's look at this stdin as an example::

    @< MODELNAME >@
    @< query({"database": "data", "fields": {"crystal-structure.a.si-value":1}, "project": ["crystal-structure.a.si-value"], "limit": 1, "query": {"kim-namespace": {"$regex": "equilibrium-crystal-structure"}, "crystal-structure.short-name": "fcc","meta.subject.kimcode": MODELNAME,"meta.runner.kimcode": {"$regex":"LatticeConstantCubicEnergy"}}}) >@


In the first line, the global variable that defines the current model that is
paired with our test is templated into a string.  The second line is a bit more
involved.  It is a query to the query `page <https://query.openkim.org/>`_ that
holds all of the data from the OpenKIM project.  In this line, we are
requesting the lattice constant (``crystal-structure.a.si-value``) from the
``equilibrium-crystal-structure`` property where the subject is the model that
we are running and the result came from the ``LatticeConstantCubicEnergy``
test.  We employ the ``project`` operator to get a single number returned. 

After templating, ``output/pipeline.stdin`` contains::

    ex_model_Ar_P_Morse__MO_831902330215_000
    5.25352661133e-10

Crafting the appropriate query can take some work.  To help with this, the
query page has an interactive form where you can hone the question you are
asking.  When you are done, the query page itself has a section which tells you
exactly what to copy paste into your code after your find the right one. For 
this example, I filled in the page like `this <https://query.openkim.org/?project=[%22crystal-structure.a.si-value%22]&fields={%22crystal-structure.a.si-value%22:1}&database=data&limit=1&query={%22kim-namespace%22:{%22$regex%22:%22equilibrium-crystal-structure%22},%22crystal-structure.short-name%22:%22fcc%22,%22meta.subject.kimcode%22:%22ex_model_Ar_P_Morse__MO_831902330215_000%22,%22meta.runner.kimcode%22:{%22$regex%22:%22LatticeConstantCubicEnergy%22}}>`_.  
At you bottom, you can see that the last howto (`pipeline.stdin.tpl`) 
is the exact line used in our test.

.. _aseref_results:

results.yaml.tpl
^^^^^^^^^^^^^^^^

The last file is just as important as the executable itself.  It describes 
where your data fits into the OpenKIM database and tells other users what
exactly was calculated.  This starts as a YAML file provided by the main KIM
website.  Next, we connect this to the output of our test by leaving blanks 
for the templating system to fill in.  

Recall that our output looks like::

    {"lattice_constant": 2.86652799316, "cohesive_energy": 4.3160000438565636}

In the file ``results.yaml``, we need to leave placeholders for these variables
for the pipeline to fill in after the test has completed.

The section::

    energy:
        kim-namespace:  tag:staff@noreply.openkim.org,2013-08-03:primitive/cohesive-energy
        source-value: 
        source-unit: 

with::

    energy:
        kim-namespace:  tag:staff@noreply.openkim.org,2013-08-03:primitive/cohesive-energy
        source-value: @<cohesive_energy>@
        source-unit:  eV


Testing everything
-------------------

Checkout the full source code in this :download:`archive
<./ASECohesiveEnergyFromQuery_fcc_Ar__TE_102111117114_000.tar.gz>`.  To use,
place in the folder ``~/openkim-repository/te``.  We can then test out our new
test using the tools provided by the pipeline.  They are on path, so you can
simply call them like other Linux utilities.  

To run every possible combination involving the test::

    pipeline_runmatches ASECohesiveEnergyFromQuery_fcc_Ar__TE_102111117114_000

or if you want to try only one run with a specific model, run::

    pipeline_runpair <testname> <modelname> inplace


Installing ASE Interface Locally
--------------------------------

If you do not wish to develop on the virtual machine, you can also install the 
OpenKIM KIMCalculator onto your local machine.

OpenKIM currently maintains an unofficial interface to the Atomic Simulation
Environment (ASE) through a Python module called `kimcalculator`.  This module
implements a calculator class much like all of the other calculators in the standard
release though it calculates quantities using the KIM API.  To install the calculator,
you must install both the OpenKIM Python bindings as well as the calculator from git
repositories hosted on github.  On standard \*nix environments, this can be done by::

    git clone https://github.com/woosong/openkim-python.git
    cd openkim-python
    [sudo] KIM_DIR=<path_to_KIM_API> python setupy.py install [--prefix=<path>]

    git clone https://github.com/mattbierbaum/openkim-kimcalculator-ase.git
    cd openkim-kimcalculator-ase 
    [sudo] python setupy.py install [--prefix=<path>]

If you have permissions and want to install to the entire system path, use the [sudo]
part.  If you do not have permissions or wish to install the package on a per-user
basis, specify a Python library path in which to install these packages (see
`python docs <http://docs.python.org/2/install/>`_).  

To use a KIM model in your calculations, you simply need to trade your calculator for
the kimcalculator.KIMCalculator object.  For example::

    calc = EMT()

changes to::

    calc = kimcalculator.KIMCalculator("AValidModelName__MO_123456789012_000")

From there, your Python program should work as usual though using the model
`AValidModelName__MO_123456789012_000`.  
