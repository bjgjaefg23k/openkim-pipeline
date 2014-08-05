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
    * :ref:`aseref_depsfile` - a file that describes our test's dependencies
    * ``README.md`` - a basic explanation of the test
    * ``LICENSE.CDDL`` - a copy of the standard license

.. _aseref_exec:

runner
^^^^^^

This is the standalone Python script that takes as input a model name
and lattice constant and calculates the energy at that constant.

The script is short enough that we should take a look at it here::

    #!/usr/bin/env python
    """
    ASE cohesive energy example test with dependencies
    
    Date: 2014/08/05
    Author: Matt Bierbaum
    """
    from ase.structure import bulk
    from kimcalculator import KIMCalculator
    from string import Template
    import os
    
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
    
    output = Template("""
    [{
        "property-id" "tag:staff@noreply.openkim.org,2014-04-15:property/cohesive-potential-energy-cubic-crystal"
        "instance-id" 0
        "short-name" {
            "source-value"  ["fcc"]
        }
        "species" {
            "source-value"  ["Ar"]
        }
        "a" {
            "source-value"  $lattice_constant
            "source-unit"   "angstrom"
        }
        "basis-atom-coordinates" {
            "source-value"  [[0.0 0.0 0.0] [0.0 0.5 0.5] [0.5 0.0 0.5] [0.5 0.5 0.0]]
        }
        "space-group" {
            "source-value"  "Fm-3m"
        }
        "cohesive-potential-energy" {
            "source-value"  $cohesive_energy
            "source-unit"   "eV"
        }
    }]""").substitute(**results)
    
    with open(os.path.abspath("output/results.edn"), "w") as f:
        f.write(output)

It begins by grabbing the model name and lattice constant from standard input.
The test assumes that the lattice constant will be input in SI units, so we
convert it to angstroms and make sure it's a float.   Next, we initialize an
ASE calculator that integrates with KIM using the model name that was provided.
We set up a single atom unit cell of fcc Ar with the given lattice constant,
and ask for the potential energy.  Finally, we pack the results into a dictionary
which we format into the final results.edn file. We directly write our formatted
property to ``output/results.edn``, a folder that is created automatically
in the pipeline framework.

.. _aseref_kimfile:

descriptor.kim
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is our KIM file as specified by the standards of the KIM project.  
In this file we limit our neighbor locator methods to ``RVEC_F`` since we
employ a parallelpiped boundary cell with only one atom. 

.. _aseref_kimspec:

kimspec.edn
^^^^^^^^^^^^

This file contains meta-data which makes it a valid KIM test in the
OpenKIM repository.  In our case, it look like::

    {
        "extended-id" "ASECohesiveEnergyFromQueryExample_fcc_Ar__TE_102111117114_000" 
        "domain" "openkim.org" 
        "title" "ASE cohesive energy test example" 
        "species" ["Ar"]
        "executables" ["runner"]
        "disclaimer" "Tutorial test using the Atomic Simulation Environment which calculates the cohesive energy"
        "resources" "mp-none"
        "kim-api-version" "1.5"
        "pipeline-api-version" "1.0"
        "properties" ["tag:staff@noreply.openkim.org,2014-04-15:property/cohesive-potential-energy-cubic-crystal"]
    }

For more information about these fields, you can look at 
`kimspec.edn docs <https://openkim.org/about-kimspec-edn/>`_.

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
    @< query({
        "project": ["a.si-value"], 
        "query": {
            "property-id": "tag:staff@noreply.openkim.org,2014-04-15:property/structure-cubic-crystal-npt", 
            "short-name.source-value": "fcc", 
            "meta.subject.kimcode": MODELNAME, 
            "meta.runner.kimcode": {"$options": "", "$regex": "LatticeConstantCubicEnergy_fcc_Ar__TE_206669103745"}
        },
        "limit": 1,
        "database": "data"
    }) >@

In the first line, the global variable that defines the current model that is
paired with our test is templated into a string.  The second line is a bit more
involved.  It is a query to the query `page <https://query.openkim.org/>`_ that
holds all of the data from the OpenKIM project.  In this line, we are
requesting the lattice constant (``a.si-value``) from the
``structure-cubic-crystal-npt`` property where the subject is the model that
we are running and the result came from the ``LatticeConstantCubicEnergy``
test.  We employ the ``project`` operator to get a single number returned. 

After templating, ``output/pipeline.stdin`` contains::

    ex_model_Ar_P_Morse__MO_831902330215_000
    5.25352661133e-10

Crafting the appropriate query can take some work.  To help with this, the
query page has an interactive form where you can hone the question you are
asking.  When you are done, the query page itself has a section which tells you
exactly what to copy paste into your code after your find the right one. For 
this example, I filled in the page like `this <https://query.openkim.org/?project=[%22a.si-value%22]&query={%22property-id%22:%22tag:staff@noreply.openkim.org,2014-04-15:property/structure-cubic-crystal-npt%22,%22short-name.source-value%22:%22fcc%22,%22meta.runner.kimcode%22:{%22$regex%22:%22LatticeConstantCubicEnergy_fcc_Ar__TE_206669103745%22},%22meta.subject.kimcode%22:%22Pair_Morse_Shifted_Jelinek_Ar__MO_831902330215_000%22}&limit=1&database=data>`_.

At you bottom, you can see that the last howto (`pipeline.stdin.tpl`) 
is the exact line used in our test.


.. _aseref_depsfile:

dependencies.edn
^^^^^^^^^^^^^^^^

This files describes the type of data that we want to receive in the file
:ref:`aseref_depsfile`. The format of this file is described in full in
these documentation pages at :ref:`pipelinedeps`.  In this example, we only
want to retrieve the lattice constant as computed by the lattice constant
test while coupled with the current model.  To indicate this, our dependency
file simply lists the lattice test indicating that we want the result of
the lattice test with the current model::

    [ "LatticeConstantCubicEnergy_fcc_Ar__TE_206669103745" ]


.. _aseref_results:


Testing everything
-------------------

Checkout the full source code in this :download:`archive
<./ASECohesiveEnergyFromQuery_fcc_Ar__TE_102111117114_000.tar.gz>` or use the
``kimitems`` utility to install it from the command line by::

    kimitems install ASECohesiveEnergyFromQueryExample_fcc_Ar__TE_102111117114_000

If you directly downloaded the source, to use, place in the folder
``~/openkim-repository/te``.  We can then test out our new test using the tools
provided by the pipeline.  They are on path, so you can simply call them like
other Linux utilities.  

To run every possible combination involving the test::

    pipeline_runmatches ASECohesiveEnergyFromQuery_fcc_Ar__TE_102111117114_000

or if you want to try only one run with a specific model, run::

    pipeline_runpair [--inplace] <testname> <modelname>


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
