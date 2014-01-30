Example tests - LAMMPS
**********************
..
    A very basic test using the Atomic Simulation Environment (ASE) and Python
    binding for the OpenKIM API.  In this test, we gather the Fe body center cubic
    lattice constant from the OpenKIM database.  Using this lattice constant, we
    set up a single atom unit cell and calculate it's energy, reporting it as the
    cohesive energy.  For a general overview on test format, have a look at the
    documentation for :ref:`desctests`.  
..
    For this example, we have adopted the descriptive KIM short name of
    ASECohesiveEnergyFromQuery_Fe_bcc and have been provided with the KIM code
    TE_102111117114_000.  

We consider here the use of the `LAMMPS Molecular Dynamics Simulator <http://lammps.sandia.gov/>`_ in constructing Tests within the OpenKIM Pipeline (hereafter, "the pipeline").  This process essentially amounts to the following steps:

#. Creating a LAMMPS input script which is accessed by the Test executable
#. Invoking LAMMPS from the Test executable
#. Parsing the LAMMPS output for the quantities of interest
#. Post-processing the quantities of interest, if necessary, and reporting the results of the Test

Two example Tests which make use of LAMMPS are detailed below.  These should already be on your box as part of the OpenKIM repository, but can also be downloaded :download:`here <./LAMMPS_tutorial_examples.tgz>`. Although not strictly necessary, both of the Tests included in this tutorial have been set up to make use of Test Drivers for the purposes of demonstration.  If you are unfamiliar with the role of Test Drivers in the pipeline or other general details of Test creation, please see :ref:`testdev`.

In the :ref:`first example Test <example1_ref>`, the user provides an initial guess at the equilibrium lattice constant of an (infinite) face-centered cubic lattice of Argon atoms.  Using this initial guess, LAMMPS attempts to compute the equilibrium lattice constant and cohesive energy by performing a static minimization of the potential energy using the Polak-Ribiere conjugate gradient method.

In the :ref:`second example Test <example2_ref>`, the user specifies a type of cubic lattice (bcc, fcc, sc, or diamond), an atomic species (e.g. 'Ar', 'Si', etc.), and a set of parameters which are used to construct a set of lattice spacings at which the cohesive energy will be computed.  In the terminology of the pipeline, this results in a cohesive energy versus lattice constant "curve."

.. _example1_ref:

Example 1: Cohesive energy & lattice constant of fcc Argon
==========================================================
:ref:`Test Driver <example1_TD_ref>`
|
:ref:`Test <example1_TE_ref>`
|
:ref:`Example Calculation <example1_calc_ref>`

.. _example1_TD_ref:

Test Driver 
---------------
Let us begin by looking at the Test Driver for the first example.  This Test Driver is constructed to compute the cohesive energy and equilibrium lattice constant of an fcc Argon lattice.  Each Test which uses this Test Driver can supply its own initial guess at the equilibrium lattice spacing.

List of files
^^^^^^^^^^^^^

    * :ref:`example1_TD_exec` - the main executable, a bash script
    * :ref:`example1_TD_kimspec` - a file which describes the metadata associated with the Test Driver
    * :ref:`example1_TD_makefile` - a Makefile
    * :ref:`example1_TD_lammpstemplate` - a LAMMPS input script template which the Test Driver processes with 'sed'
    * ``README.txt`` - a file which contains a basic explanation of the Test Driver
    * ``LICENSE.CDDL`` - a copy of the `CDDL license <http://opensource.org/licenses/CDDL-1.0>`_

.. _example1_TD_exec:

LammpsExample__TD_567444853524_000
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code-block:: bash

    #!/usr/bin/env bash

    # Author: Daniel S. Karls (karl0100 |AT| umn DOT edu), University of Minnesota
    # Date: 9/13/2013

    # This example Test Driver computes the cohesive energy and equilibrium
    # lattice constant for an FCC argon lattice using Polak-Ribiere
    # conjugate gradient static minimization in LAMMPS and an initial guess
    # at the equilibrium lattice spacing supplied by the user through pipeline.stdin.tpl.

    # Define function which outputs to stderr
    echoerr() { echo "$@" 1>&2; }
    
    # Read the KIM Model name and initial lattice constant from pipeline.stdin.tpl
    # (the former is passed using @< MODELNAME >@, which the
    # pipeline will automatically fill in once a compatible Model is found).
    echo "Please enter a KIM Model name:"
    read modelname
    echo "Please enter an initial lattice constant (Angstroms):"
    read initial_lattice_constant
    
    # Replace the string 'sed_model_string' in the lammp.in.template input file
    # script template with the name of the KIM Model being used.  Also replace
    # the string 'sed_initial_lattice_constant_string' with the value supplied
    # through stdin.
    # The resulting  file will be stored in the Test Result folder (which may be
    # referenced as the 'output' directory).
    thisdir=`dirname "$0"` # The directory of this Test Driver executable
    sed s/sed_model_string/"$modelname"/ ""$thisdir"/lammps.in.template" > output/lammps.in
    sed -i "s/sed_initial_lattice_constant_string/$initial_lattice_constant/" output/lammps.in
    
    # Run LAMMPS using the lammps.in input file and write the output to lammps.log
    lammps < output/lammps.in > output/lammps.log
    
    # Parse the LAMMPS output log and extract the final pressure (to indicate how converged it is to 0),
    # cohesive energy, and equilibrium lattice constant.
    numberoflines=`awk 'END{print NR}' output/lammps.log`
    finalpressure=`awk "NR==$numberoflines-2" output/lammps.log | awk '{print $(NF-1)}'`
    ecohesive=`awk "NR==$numberoflines-1" output/lammps.log | awk '{print $(NF-1)}'`
    latticeconstant=`awk "NR==$numberoflines" output/lammps.log | awk '{print $(NF-1)}'`
    
    # Check that the results we obtained are actually numbers (in case there was a LAMMPS error of some sort)
    if ! [[ $finalpressure =~ ^[0-9.e-]+ ]] ; then
        echo "Error: Final pressure parsed from LAMMPS log is not a numeric value.  Check the LAMMPS log for errors.  Exiting..."
        echoerr "Error: Final pressure parsed from LAMMPS log is not a numeric value.  Check the LAMMPS log for errors.  Exiting..."
        exit 1
    elif ! [[ $ecohesive =~ ^[0-9.e-]+ ]] ; then
        echo "Error: Cohesive energy parsed from LAMMPS log is not a numeric value.  Check the LAMMPS log for errors.  Exiting..."
        echoerr "Error: Cohesive energy parsed from LAMMPS log is not a numeric value.  Check the LAMMPS log for errors.  Exiting..."
        exit 1
    elif ! [[ $latticeconstant =~ ^[0-9.e-]+ ]] ; then
        echo "Error: Equilibrium lattice constant parsed from LAMMPS log is not a numeric value.  Check the LAMMPS log for errors.  Exiting..."
        echoerr "Error: Equilibrium lattice constant parsed from LAMMPS log is not a numeric value.  Check the LAMMPS log for errors.  Exiting..."
    exit 1
    fi
    
    # Create a JSON dictionary of the Test Results.  This will be used to parse through the results.yaml.tpl Jinja template
    # found in the directories of Tests which are derived from this Test Driver (e.g. LammpsExample__TE_565333229701_000)
    thisdir=`dirname "$0"`
    JSONresults="{ \"latticeconstant\": \"$latticeconstant\", \"cohesiveenergy\": \"$ecohesive\", \"finalpressure\": \"$finalpressure\" }"
    
    # Print the JSON dictionary of results as the *last* line of stdout for the pipeline to catch
    echo "$JSONresults"

We begin by reading the Model name and the initial lattice constant from stdin.  The instantiations of these are contained in the :ref:`example1_TE_stdin` file of the Test itself.  The Model name and initial lattice constant are then used to replace the corresponding placeholder strings in :ref:`example1_TD_lammpstemplate` to create a functioning LAMMPS input script, ``lammps.in``, in the Test Result directory (``output/``).  LAMMPS is then called using ``lammps.in`` as an input script and the resulting output is redirected to a file named ``lammps.log`` in the Test Result directory.  After the quantities of interest in the LAMMPS log file are parsed, a JSON dictionary containing the results is created and printed as the last line of stdout.  Note that the "keys" (variable names)  contained in this JSON dictionary, i.e. "latticeconstant", "cohesiveenergy", and "finalpressure", can be chosen arbitrarily so long as they correspond to the variable names in the template that is used by the Test to report its results (:ref:`example1_TE_results`).   Moreover, note that the name of this file must be the extended KIM ID of the Test Driver.

.. _example1_TD_kimspec:

kimspec.yaml
^^^^^^^^^^^^
This YAML-formatted file contains metadata associated with the Test Driver.  More information on these files can be found `here <https://kim-items.openkim.org/kimspec-format>`_. This file must always be named ``kimspec.yaml``.

.. code-block:: yaml

    extended-id: LammpsExample__TD_567444853524_000
    title: "LammpsExample: compute cohesive energy and equilibrium lattice constant of fcc Argon."
    description: "This example Test Driver illustrates the use of LAMMPS in the openkim-pipeline to compute the equilibrium lattice spacing
       and cohesive energy of fcc Argon using Polak-Ribiere conjugate gradient minimization in LAMMPS and an initial guess at the equilibrium
       lattice spacing supplied by the user through pipeline.stdin.tpl."
    notes: "Submitted by Daniel S. Karls (karl0100 |AT| umn DOT edu), University of Minnesota."
    domain: openkim.org

.. _example1_TD_makefile:

Makefile
^^^^^^^^
As there is no need to compile :ref:`example1_TD_exec` since it is a bash script, the Makefile is uninteresting. ::

    all:
                @echo "Nothing to make"

    clean:
                @echo "Nothing to clean"

.. _example1_TD_lammpstemplate:

lammps.in.template
^^^^^^^^^^^^^^^^^^
This file is processed by :ref:`example1_TD_exec` using the 'sed' command line utility and the information entered on stdin through :ref:`example1_TE_stdin`.  The processed file is then written to the final LAMMPS input script which is run (``lammps.in`` in the Test Result directory). Note that when using a KIM Model within LAMMPS, the appropriate LAMMPS 'pair_style' to use is `pair_style kim <http://lammps.sandia.gov/doc/pair_kim.html>`_. ::

    # Define unit set and class of atomic model
    units metal
    atom_style atomic
    
    # Periodic boundary conditions along all three dimensions
    boundary p p p
    
    # Create an FCC lattice with the lattice spacing supplied supplied by the user
    # using a single conventional (orthogonal) unit cell
    lattice fcc sed_initial_lattice_constant_string
    region box block 0 1 0 1 0 1 units lattice
    create_box 1 box
    create_atoms 1 box
    mass 1 39.948
    
    # Specify which KIM Model to use, letting LAMMPS compute the virial/pressure
    pair_style kim LAMMPSvirial sed_model_string
    pair_coeff * * Ar
    
    # Set what thermodynamic information to print to log
    thermo_style custom step atoms xlo xhi ylo yhi zlo zhi pe press pxx pyy pzz pxy pxz pyz
    thermo 10 # Print every 10 timesteps
    
    # Set what information to write to dump file
    dump id all custom 10 output/lammps.dump id type x y z fx fy fz
    dump_modify id format "%d %d %16.7f %16.7f %16.7f %16.7f %16.7f %16.7f"
    
    # Set boundary conditions to be stress-free
    fix 1 all box/relax iso 0.0
    
    # Perform static minimization using the Polack-Ribiere conjugate gradient method.
    # The first argument is a convergence tolerance for the energy, the second argument
    # is a convergence tolerance for the forces, and the latter two arguments set the
    # maximum number of allowed iterations and force/energy evaluations, respectively.
    minimize 1e-16 1e-16 2000 100000
    
    # Define auxiliary variables to contain cohesive energy and equilibrium lattice constant
    variable poteng    equal "c_thermo_pe"
    variable natoms    equal "count(all)"
    variable ecohesive equal "-v_poteng/v_natoms"
    variable pressure  equal "c_thermo_press"
    variable a         equal "lx"
    
    # Output cohesive energy and equilibrium lattice constant
    print "Final pressure = ${pressure} bar"
    print "Cohesive energy = ${ecohesive} eV/atom"
    print "Equilibrium lattice constant = ${a} angstrom"

Neither the contents nor name of this file are standardized within the pipeline, but instead are left up to the Test writer.

.. _example1_TE_ref:

Test 
--------
Next, we inspect a Test which uses the above Test Driver.  In this case, this Test corresponds to one particular initial guess at the lattice constant, 5.3 Angstroms.

.. _example1_TE_listoffiles:

List of files
^^^^^^^^^^^^^

    * :ref:`example1_TE_exec` - the main executable, a python script
    * :ref:`example1_TE_kimfile` - a KIM descriptor file which outlines the capabilities of the Test
    * :ref:`example1_TE_kimspec` - a file which describes the metadata associated with the Test
    * :ref:`example1_TE_makefile` - a Makefile
    * :ref:`example1_TE_stdin` - a Jinja template file used to provide input on stdin
    * :ref:`example1_TE_results` - a Jinja template file used to report the results of the Test
    * ``README.txt`` - a file which contains a basic explanation of the Test 
    * ``LICENSE.CDDL`` - a copy of the `CDDL license <http://opensource.org/licenses/CDDL-1.0>`_ 

.. _example1_TE_exec:

LammpsExample__TE_565333229701_000
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In the case where a Test uses a Test Driver, the contents of its executable file can be a copy of the following standard python script

.. code-block:: python

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

As with the Test Driver, the name of this file must be the extended KIM ID of the Test.

.. _example1_TE_kimfile:

LammpsExample__TE_565333229701_000.kim
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The .kim descriptor file outlines the operational parameters of the Test, including the units it uses, the atomic species it supports, the neighborlist methods it contains, what information it passes to a Model, and what information it expects to receive from a Model.  The name of this file should be <extended KIM ID>.kim. ::

    TEST_NAME        := LammpsExample__TE_565333229701_000
    Unit_Handling    := flexible
    Unit_length      := A
    Unit_energy      := eV
    Unit_charge      := e
    Unit_temperature := K
    Unit_time        := ps
    
    SUPPORTED_ATOM/PARTICLES_TYPES:
    Ar spec 18
    
    CONVENTIONS:
    ZeroBasedLists    flag
    Neigh_BothAccess  flag
    NEIGH_PURE_H      flag
    NEIGH_PURE_F      flag
    NEIGH_RVEC_F      flag
    
    MODEL_INPUT:
    numberOfParticles            integer  none    []
    numberParticleTypes          integer  none    []
    particleTypes                integer  none    [numberOfParticles]
    coordinates                  double   length  [numberOfParticles,3]
    numberContributingParticles  integer  none    []
    get_neigh                    method   none    []
    neighObject                  pointer  none    []
    
    MODEL_OUTPUT:
    compute  method  none    []
    destroy  method  none    []
    cutoff   double  length  []
    energy   double  energy  []
    forces   double  force   [numberOfParticles,3]

.. warning:: Although a .kim descriptor file must be included with every Test, please bear in mind that this file is not explicitly used by LAMMPS, but instead only by the pipeline when determining compatible Test-Model pairings.  Rather, whenever LAMMPS is run with 'pair_style kim', it dynamically creates a .kim descriptor file for the Test which remains unseen by the user.  The contents of this .kim file depend on the details of the LAMMPS input script, as well as the way LAMMPS is invoked.  For example, the "CLUSTER" neighborlisting method is only included in this .kim file if a single processor is being used and none of the directions are periodic.  Moreover, note that LAMMPS is currently not compatible with the MI_OPBC_H or MI_OPBC_F neighborlisting methods.  The code which writes the .kim file is located inside of the ``pair_kim.cpp`` source file under ``/src/KIM/`` in the LAMMPS root directory.  An up-to-date version of ``pair_kim.cpp`` can also be viewed in the `LAMMPS git mirror <http://git.icms.temple.edu/git/>`_ by going to "tree" under "lammps-ro.git" and proceeding to ``/src/KIM/``.

.. _example1_TE_kimspec:

kimspec.yaml
^^^^^^^^^^^^
This YAML-formatted file contains metadata associated with the Test.  More information on these files can be found `here <https://kim-items.openkim.org/kimspec-format>`_.  This file must always be named ``kimspec.yaml``.

.. code-block:: yaml

    extended-id: LammpsExample__TE_565333229701_000
    test-driver: LammpsExample__TD_567444853524_000
    title: "LammpsExample: compute cohesive energy and equilbrium lattice constant for fcc Argon"
    species: Ar
    description: "This example Test illustrates the use of LAMMPS in the openkim-pipeline to compute the cohesive energy of fcc Argon using
       conjugate gradient minimization with an initial guess of 5.3 for the equilibrium lattice constant."
    notes: "Submitted by Daniel S. Karls (karl0100 |AT| umn DOT edu), University of Minnesota"
    domain: openkim.org

.. _example1_TE_makefile:

Makefile
^^^^^^^^
As there is no need to compile :ref:`example1_TE_exec`, the Makefile is uninteresting. ::

    all:
                @echo "Nothing to make"

    clean:
                @echo "Nothing to clean"

.. _example1_TE_stdin:

pipeline.stdin.tpl
^^^^^^^^^^^^^^^^^^
This Jinja template file is used to input information to the Test (or its Test Driver, in this case) on stdin.  Whatever is inside of ``@<...>@`` is interpreted as Python code which evaluates to a variable.  Code blocks are also possible with ``@[...]@``.  One subtlety is that when a Test uses a Test Driver, the first line in this file should contain an evaluation of the path of the Test Driver's executable.

Here, we begin by specifying the path of the Test Driver.  We then use ``@< MODELNAME >@``, which the pipeline will automatically replace at run-time with the extended KIM ID of the Model being run against the Test.  Finally, the initial guess of 5.3 Angstroms for the equilibrium lattice constant is fed to the Test Driver. ::

    @< path("LammpsExample__TD_567444853524_000") >@
    @< MODELNAME >@
    5.3

This file must always be named ``pipeline.stdin.tpl``.  Further explanation of these files can be found :ref:`here <pipelineindocs>`. 

.. _example1_TE_results:

results.yaml.tpl
^^^^^^^^^^^^^^^^
This Jinja template file is used by the Test to report its results.  Separate document blocks are demarcated by ``---``, and in this case the Test reports two properties: ``equilibrium-crystal-structure`` and ``cohesive-energy``.  The ``equilibrium-crystal-structure`` property contains the ``crystal-structure`` and ``nvt`` primitives, while the ``cohesive-energy`` property contains the ``crystal-structure``, ``cohesive-energy``, and ``equilibrium-ensemble-npt`` primitives.

::

    ---
    crystal-structure:
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/crystal-structure
      a:
        source-unit: angstrom
        source-value: @<latticeconstant>@
      alpha:
        source-units: degrees
        source-value: 90
      b:
        source-unit: angstrom
        source-value: @<latticeconstant>@
      beta:
        source-units: degrees
        source-value: 90
      c:
        source-unit: angstrom
        source-value: @<latticeconstant>@
      gamma:
        source-units: degrees
        source-value: 90
      short-name:
      - fcc
      space-group: Fm-3m
      wyckoff-site:
      - code: 4a
        fract-x:
          source-unit: 1
          source-value: 0
        fract-y:
          source-unit: 1
          source-value: 0
        fract-z:
          source-unit: 1
          source-value: 0
        set-or-measured: set
        species: Ar
    nvt:
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/equilibrium-ensemble-nvt
      temperature:
        source-unit: K
        source-value: 0
    kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:property/equilibrium-crystal-structure
    ---
    crystal-structure:
      a:
        source-unit: angstrom
        source-value: @<latticeconstant>@
      alpha:
        source-units: degrees
        source-value: 90
      b:
        source-unit: angstrom
        source-value: @<latticeconstant>@
      beta:
        source-units: degrees
        source-value: 90
      c:
        source-unit: angstrom
        source-value: @<latticeconstant>@
      gamma:
        source-units: degrees
        source-value: 90
      kim-ns: tag:staff@noreply.openkim.org,2013-08-03:primitive.crystal-structure
      short-name:
      - fcc
      space-group: Fm-3m
      wyckoff-site:
      - code: 4a
        fract-x:
          source-unit: 1
          source-value: 0
        fract-y:
          source-unit: 1
          source-value: 0
        fract-z:
          source-unit: 1
          source-value: 0
        set-or-measured: set
        species: Ar
    energy:
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/cohesive-energy
      source-unit: eV
      source-value: @<cohesiveenergy>@
    npt:
      kim-ns: tag:staff@noreply.openkim.org,2013-08-03:primitive/equilibrium-ensemble-npt
      temperature:
        source-unit: K
        source-value: 0
      pressure:
        source-unit: bar
        source-value: @<finalpressure>@
    kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:property/cohesive-energy

Note that the variable names used within the ``@<...>@`` exactly match the key names in the JSON dictionary output by :ref:`example1_TD_exec`.  Using the JSON dictionary printed by the Test Driver, the pipeline automatically parses through ``results.yaml.tpl`` and replaces the template instances with the corresponding values found in the JSON dictionary.  This process renders a YAML file named ``results.yaml`` which is placed in the Test Result directory.

Although not strictly required, users are strongly encouraged to use the official Test Result templates made available on openkim.org.

This file must be named ``results.yaml.tpl``.

.. warning:: LAMMPS does not always use "derived" sets of units, as the KIM API does.  In this example, LAMMPS uses 'units metal' as instructed to in :ref:`example1_TD_lammpstemplate`.  In this system of units, for example, pressure is reported in bars rather than eV/Angstrom^3 even though the unit for energy is eV and the unit for length is Angstroms.  Therefore, one should pay attention to what units are actually being reported.  However, this is easy to resolve, since any units defined within `GNU Units <http://www.gnu.org/software/units/>`_ can be specified as the ``source-unit`` field in ``results.yaml.tpl``.  Above, the ``pressure`` key in the ``equilibrium-ensemble-npt`` primitive of the ``cohesive-energy`` property has had ``source-unit: bar`` specified since no post-conversion of the units of the LAMMPS pressure was done.

.. _example1_calc_ref:

Example Calculation
-------------------
To verify that the Test Driver and Test above work, let us try running the Test against a particular Model, ``Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_000``.  In order to run a specific Test-Model pair, the pipeline provides a utility named ``pipeline_runpair`` which can be invoked in the following manner::

    pipeline_runpair LammpsExample__TE_565333229701_000 Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_000

which yields as output something similar to the following::

    2014-01-28 20:08:37,837 - INFO - pipeline.development - Running combination <<Test(LammpsExample__TE_565333229701_000)>, <Model(Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_000)>
    2014-01-28 20:08:37,868 - INFO - pipeline.compute - running <Test(LammpsExample__TE_565333229701_000)> with <Model(Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_000)>
    2014-01-28 20:08:37,872 - INFO - pipeline.template - attempting to process '/home/openkim/openkim-repository/te/LammpsExample_runningf96016a1-8857-11e3-8596-4005d10d911c__TE_565333229701_000/pipeline.stdin.tpl' for ('LammpsExample__TE_565333229701_000','Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_000')
    2014-01-28 20:08:37,880 - INFO - pipeline.compute - launching run...
    2014-01-28 20:08:38,000 - INFO - pipeline.compute - Run completed in 0.12008380889892578 seconds
    2014-01-28 20:08:38,150 - INFO - pipeline.compute - Copying the contents of /home/openkim/openkim-repository/te/LammpsExample_runningf96016a1-8857-11e3-8596-4005d10d911c__TE_565333229701_000/output to /home/openkim/openkim-repository/tr/f96016a1-8857-11e3-8596-4005d10d911c

In this case, the last line of the output indicates that the results of the calculation have been copied to ``/home/openkim/openkim-repository/tr/f96016a1-8857-11e3-8596-4005d10d911c/``.  Examining ``pipeline.stdout``, we can see the JSON dictionary printed by the Test Driver::
    
    Please enter a KIM Model name:
    Please enter an initial lattice constant (Angstroms):
    { "latticeconstant": "5.24859000000002", "cohesiveenergy": "0.0865055077405508", "finalpressure": "-1.44622588926135" }

The JSON dictionary indicates that the cohesive energy returned by the Test is 0.0865055077405508 eV and the equilibrium lattice constant is 5.24859000000002 Angstroms.  Since the final pressure reported by LAMMPS is only -1.44622588926135 bar, we can safely assume that the calculation has converged to a relaxed state.  These results compare favorably to the results of the ``ex_test_Ar_FCCcohesive_MI_OPBC``, ``ex_test_Ar_FCCcohesive_NEIGH_PURE``, and ``ex_test_Ar_FCCcohesive_NEIGH_RVEC`` example Tests included with the API when run against ``Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_000``.  We can also inspect the formal results file generated by the Test, ``results.yaml``:

.. code-block:: yaml

    ---
    crystal-structure:
      a:
        si-unit: m
        si-value: 5.24859e-10
        source-unit: angstrom
        source-value: 5.24859000000002
      alpha:
        source-units: degrees
        source-value: 90
      b:
        si-unit: m
        si-value: 5.24859e-10
        source-unit: angstrom
        source-value: 5.24859000000002
      beta:
        source-units: degrees
        source-value: 90
      c:
        si-unit: m
        si-value: 5.24859e-10
        source-unit: angstrom
        source-value: 5.24859000000002
      gamma:
        source-units: degrees
        source-value: 90
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/crystal-structure
      short-name:
      - fcc
      space-group: Fm-3m
      wyckoff-site:
      - code: 4a
        fract-x:
          si-unit: '1'
          si-value: 0.0
          source-unit: 1
          source-value: 0
        fract-y:
          si-unit: '1'
          si-value: 0.0
          source-unit: 1
          source-value: 0
        fract-z:
          si-unit: '1'
          si-value: 0.0
          source-unit: 1
          source-value: 0
        set-or-measured: set
        species: Ar
    kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:property/equilibrium-crystal-structure
    nvt:
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/equilibrium-ensemble-nvt
      temperature:
        si-unit: K
        si-value: 0.0
        source-unit: K
        source-value: 0
    ---
    crystal-structure:
      a:
        si-unit: m
        si-value: 5.24859e-10
        source-unit: angstrom
        source-value: 5.24859000000002
      alpha:
        source-units: degrees
        source-value: 90
      b:
        si-unit: m
        si-value: 5.24859e-10
        source-unit: angstrom
        source-value: 5.24859000000002
      beta:
        source-units: degrees
        source-value: 90
      c:
        si-unit: m
        si-value: 5.24859e-10
        source-unit: angstrom
        source-value: 5.24859000000002
      gamma:
        source-units: degrees
        source-value: 90
      kim-ns: tag:staff@noreply.openkim.org,2013-08-03:primitive.crystal-structure
      short-name:
      - fcc
      space-group: Fm-3m
      wyckoff-site:
      - code: 4a
        fract-x:
          si-unit: '1'
          si-value: 0.0
          source-unit: 1
          source-value: 0
        fract-y:
          si-unit: '1'
          si-value: 0.0
          source-unit: 1
          source-value: 0
        fract-z:
          si-unit: '1'
          si-value: 0.0
          source-unit: 1
          source-value: 0
        set-or-measured: set
        species: Ar
    energy:
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/cohesive-energy
      si-unit: kg m^2 / s^2
      si-value: 1.3859709e-20
      source-unit: eV
      source-value: 0.0865055077405508
    kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:property/cohesive-energy
    npt:
      kim-ns: tag:staff@noreply.openkim.org,2013-08-03:primitive/equilibrium-ensemble-npt
      pressure:
        si-unit: kg / m s^2
        si-value: -144622.59
        source-unit: bar
        source-value: -1.44622588926135
      temperature:
        si-unit: K
        si-value: 0.0
        source-unit: K
        source-value: 0

where one can notice that the pipeline automatically creates the ``si-unit`` and ``si-value`` fields for its own internal storage purposes.

.. note:: The ``inplace`` flag can be placed after the Model name when invoking ``pipeline_runpair`` in order to redirect the test results to a directory named ``output`` inside of the Test directory.
.. note:: The ``pipeline_runmatches`` command can be used to attempt to run a Test against all Models whose .kim files indicate they are compatible with the Test.

.. _example2_ref:

Example 2: Cohesive energy vs. lattice constant curve
=====================================================
:ref:`Test Driver <example2_TD_ref>`
|
:ref:`Test <example2_TE_ref>`
|
:ref:`Example Calculation <example2_calc_ref>`

Please ensure you understand :ref:`Example 1 <example1_ref>` before continuing with this example.

.. _example2_TD_ref:

Test Driver
---------------
This Test Driver is constructed to compute a cohesive energy versus lattice constant "curve" for a cubic lattice of a given species.  The lattice constants for which the cohesive energy is computed are specified by a set of parameters given by the user.

.. _example2_TD_listoffiles: 

List of files
^^^^^^^^^^^^^

    * :ref:`example2_TD_exec` - the main executable, a bash script
    * :ref:`example2_TD_kimspec` - a file which describes the metadata associated with the Test Driver
    * :ref:`example2_TD_makefile` - a Makefile
    * :ref:`example2_TD_lammpstemplate` - a LAMMPS input script template which the Test Driver processes with 'sed'
    * ``README.txt`` - a file which contains a basic explanation of the Test Driver
    * ``LICENSE.CDDL`` - a copy of the `CDDL license <http://opensource.org/licenses/CDDL-1.0>`_
    * ``test_generator.json`` - a file used by ``testgenie`` to generate Tests from this Test Driver
    * ``test_template/`` - a directory containing template files used by ``testgenie`` to generate Tests from this Test Driver

.. _example2_TD_exec:

LammpsExample2__TD_887699523131_000
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code-block:: bash

    #!/usr/bin/env bash
    
    # Author: Daniel S. Karls (karl0100 |AT| umn DOT edu), University of Minnesota
    # Date: 9/13/2013
    
    # This example Test Driver illustrates the use of LAMMPS in the openkim-pipeline to compute a cohesive energy versus lattice constant curve
    # for a given cubic lattice (fcc, bcc, sc, diamond) of a single given species.  The curve is computed for lattice constants ranging from a_min
    # to a_max, with most samples being about a_0 (a_min, a_max, and a_0 are specified via stdin. a_0 is typically approximately equal to the equilibrium
    # lattice constant.).  The precise scaling of sample points going from a_min to a_0 and from a_0 to a_max is specified by two separate parameters
    # passed from stdin.
    
    # Define function which prints to stderr
    echoerr() { echo "$@" 1>&2; }
    
    # Read the KIM Model name from stdin (this is passed through pipeline.stdin.tpl using the @< MODELNAME >@, which the pipeline will automatically fill
    # in once a compatible Model is found). Also pass the species, atomic mass (in g/mol), type of cubic lattice (bcc, fcc, sc, or diamond), a_0, a_min,
    # number of sample spacings between a_min and a_0, a_max, number of sample spacings between a_0 and a_max, and the two parameters governing the
    # distribution of sample spacings around a_0 compared to a_min/a_max respectively.  Please see README.txt for more details on these parameters and
    # how they are used.
    echo "Please enter a valid KIM Model extended-ID:"
    read modelname
    echo "Please enter the species symbol (e.g. Si, Au, Al, etc.):"
    read element
    echo "Please enter the atomic mass of the species (g/mol):"
    read mass
    echo "Please enter the lattice type (bcc, fcc, sc, or diamond):"
    read latticetypeinput
    echo "Please specify a lattice constant (referred to as a_0 below) about which the energy will be computed (This will usually be the equilibrium lattice constant.\
      Most of the volumes sampled will be about this lattice constant.):"
    read a_0
    echo "Please specify the smallest lattice spacing (referred to as a_min below) at which to compute the energy:"
    read a_min
    echo "Please enter the number of sample lattice spacings to compute which are >= a_min and < a_0 (one of these sample lattice spacings will be equal to a_min):"
    read N_lower
    echo "Please specify the largest lattice spacing (referred to as a_max below) at which to compute the energy:"
    read a_max
    echo "Please enter the number of sample lattice spacings to compute which are > a_0 and <= a_max (one of these sample lattice spacings will be equal to a_max):"
    read N_upper
    echo "Please enter a value of the "lower sample spacing parameter" (see README.txt for more details):"
    read samplespacing_lower
    echo "Please enter a value of the "upper sample spacing parameter" (see README.txt for more details):"
    read samplespacing_upper
    
    # Check that lattice constants are positive and that a_min < a_0 < a_max
    a_mincheck=`echo $a_min | awk '{if($1 <= 0.0) print "Not positive"} {}'`
    if [ "$a_mincheck" == "Not positive" ]; then
    echo "Error: a_min read in must be a positive number.  Exiting..."
    echoerr "Error: a_min read in must be a positive number.  Exiting..."
    exit 1
    fi
    
    a_0check=`echo $a_0 $a_min | awk '{if($1 <= $2) print "Not greater than a_min"}'`
    if [ "$a_0check" == "Not greater than a_min" ]; then
    echo "Error: a_0 read in must be strictly greater than a_min.  Exiting..."
    echoerr "Error: a_0 read in must be strictly greater than a_min.  Exiting..."
    exit 1
    fi
    
    a_maxcheck=`echo $a_max $a_0 | awk '{if($1 <= $2) print "Not greater than a_0"}'`
    if [ "$a_maxcheck" == "Not greater than a_0" ]; then
    echo "Error: a_max read in must be strictly greater than a_0.  Exiting..."
    echoerr "Error: a_max read in must be strictly greater than a_0.  Exiting..."
    exit 1
    fi
    
    # Check that the number of spacings are positive
    N_lowercheck=`echo $N_lower | awk '{if($1 <= 0) print "Not positive"}'`
    if [ "$N_lowercheck" == "Not positive" ]; then
    echo "Error: N_lower read in must be a positive number.  Exiting..."
    echoerr "Error: N_lower read in must be a positive number.  Exiting..."
    exit 1
    fi
    
    N_uppercheck=`echo $N_upper | awk '{if($1 <= 0) print "Not positive"}'`
    if [ "$N_uppercheck" == "Not positive" ]; then
    echo "Error: N_upper read in must be a positive number.  Exiting..."
    echoerr "Error: N_upper read in must be a positive number.  Exiting..."
    exit 1
    fi
    
    # Check that samplespacing parameters are > 1
    spacingparamcheck=`echo $samplespacing_lower $samplespacing_upper | awk '{if($1 <= 1.0 && $2 <=1.0) print 1; else if($1 <= 1.0) print 2; else if($2 <= 1.0) print 3; else print 4}'`
    if [ "$spacingparamcheck" == 1 ]; then
    echo "Error: lower and upper sample spacing parameters must both be strictly greater than 1."
    echoerr "Error: lower and upper sample spacing parameters must both be strictly greater than 1."
    exit 1
    elif [ "$spacingparamcheck" == 2 ]; then
    echo "Error: lower sample spacing parameter must be strictly greater than 1.  Exiting."
    echoerr "Error: lower sample spacing parameter must be strictly greater than 1.  Exiting."
    exit 1
    elif [ "$spacingparamcheck" == 3 ]; then
    echo "Error: upper sample spacing parameter must be strictly greater than 1.  Exiting."
    echoerr "Error: upper sample spacing parameter must be strictly greater than 1.  Exiting."
    exit 1
    fi
    
    # Identify which of the cubic lattice types (bcc,fcc,sc,diamond) the user entered (case-insensitive).
    if [ `echo $latticetypeinput | tr [:upper:] [:lower:]` = `echo bcc | tr [:upper:] [:lower:]`  ]; then
    latticetype="bcc"
    space_group="Im-3m"
    wyckoffcode="2a"
    elif [ `echo $latticetypeinput | tr [:upper:] [:lower:]` = `echo fcc | tr [:upper:] [:lower:]` ]; then
    latticetype="fcc"
    space_group="Fm-3m"
    wyckoffcode="4a"
    elif [ `echo $latticetypeinput | tr [:upper:] [:lower:]` = `echo sc | tr [:upper:] [:lower:]` ]; then
    latticetype="sc"
    space_group="Pm-3m"
    wyckoffcode="1a"
    elif [ `echo $latticetypeinput | tr [:upper:] [:lower:]` = `echo diamond | tr [:upper:] [:lower:]` ]; then
    latticetype="diamond"
    space_group="Fd-3m"
    wyckoffcode="8a"
    else
    echo "Error: This Test supports only cubic lattices (specified by 'bcc', 'fcc', 'sc', or 'diamond'). Exiting..."
    echoerr "Error: This Test supports only cubic lattices (specified by 'bcc', 'fcc', 'sc', or 'diamond'). Exiting..."
    exit 1
    fi
    
    # Define which lattice constants at which the energy will be computed.  See README.txt for more details.
    latticeconst=`echo $a_0 $a_min $N_lower $a_max $N_upper $samplespacing_lower $samplespacing_upper | awk '{for (i=0;i<=$3;++i){printf "%f ",$2+($1-$2)*log(1+i*($6-1)/$3)/log($6)}}\
    {for (i=$5-1;i>=0;--i){printf "%f ",$1+($4-$1)*(1-log(1+i*($7-1)/$5)/log($7))}}'`
    read -a lattice_const <<< "$latticeconst"
    numberofspacings=`expr $N_lower + $N_upper + 1`
    
    # Replace placeholder strings in the lammp.in.template input file script template.  The resulting
    # lammps input file (lammps.in)  will be stored in the Test Result folder (which may be referenced
    # as the 'output' directory).
    thisdir=`dirname "$0"` # Directory of this Test Driver executable
    sed s/sed_model_string/"$modelname"/ ""$thisdir"/lammps.in.template" > output/lammps.in
    sed -i "s/sed_species_string/$element/" output/lammps.in
    sed -i "s/sed_mass_string/$mass/" output/lammps.in
    sed -i "s/sed_latticetype_string/$latticetype/" output/lammps.in
    sed -i "s/sed_numberofspacings_string/$numberofspacings/" output/lammps.in
    sed -i "s/sed_latticeconst_string/$latticeconst/" output/lammps.in
    
    # Run LAMMPS using the lammps.in input file and write to lammps.log
    lammps -in output/lammps.in > output/lammps.log
    
    # Parse LAMMPS output log and extract the cohesive energies corresponding to each lattice spacing into an array
    read -a cohesive_energy <<< `grep "Cohesive energy = [0-9.e-]* eV/atom" output/lammps.log | cut -d' ' -f4 | sed ':a;N;$!ba;s/\n/ /g'`
    
    # Build a JSON dictionary of results.  This will be used to parse through the results.yaml.tpl Jinja template found in the directories of Tests which are
    # derived from this Test Driver (e.g. LammpsExample2_Ar_fcc__TE_778998786610_000).
    JSONresults="{ \"crystal_structure\": \"$latticetype\",  \"element\": \"$element\", \"wyckoff_code\": \"$wyckoffcode\", \"space_group\": \"$space_group\",\
     \"numberofspacings\": \"$numberofspacings\", \"latticeconstantarray\": ["
    
    for ((i=1; i<=$numberofspacings;++i))
    do
    j=`expr $i - 1`
        JSONresults="$JSONresults {\"lattice_constant\": \"${lattice_const[$j]}\"}"
    if [ "$i" -lt "$numberofspacings" ]; then
        JSONresults="$JSONresults,"
    fi
    done
    
    JSONresults="$JSONresults], \"cohesiveenergyarray\": ["
    
    for ((i=1; i<=$numberofspacings;++i))
    do
    j=`expr $i - 1`
    # Check to see that the cohesive energies parsed from LAMMPS are actually numbers (in case there was a LAMMPS error of some sort)
    if ! [[ "${cohesive_energy[$j]}" =~ ^[0-9e.-]+ ]] ; then
        echo "Error: Cohesive energies parsed from LAMMPS are not numerical.  Check the LAMMPS log for errors.  Exiting..."
        echoerr "Error: Cohesive energies parsed from LAMMPS are not numerical.  Check the LAMMPS log for errors.  Exiting..."
        exit 1
    fi
    ecoh=`echo ${cohesive_energy[$j]} | awk '{print $1*(-1)}'`
        JSONresults="$JSONresults {\"cohesive_energy\": \"${ecoh}\"}"
    if [ "$i" -lt "$numberofspacings" ]; then
        JSONresults="$JSONresults,"
    fi
    done
    
    JSONresults="$JSONresults]}"
    
    # Print the JSON dictionary of results as the *last* line of stdout for the pipeline to catch.
    echo "$JSONresults"

The Test Driver begins by reading the Model name, atomic species, atomic mass, and lattice type from stdin.  The parameters which determine the precise lattice spacings for which the cohesive energy will be computed are then read in (see ``README.txt`` for further explanation of these parameters).  After some error-checking is done to ensure that the user-specified parameters are valid, the array of lattice constants and the number of lattice constants are computed.  Once the LAMMPS input template, :ref:`example2_TD_lammpstemplate` is processed with 'sed' and a functioning LAMMPS input script, ``lammps.in`` is written to the Test Result directory (``output/``), LAMMPS is invoked.

The LAMMPS input script for this example utilizes the `next <http://lammps.sandia.gov/doc/next.html>`_ and `jump <http://lammps.sandia.gov/doc/jump.html>`_ commands within LAMMPS in order to loop over the set of lattice constants, and the result for each lattice constant is successively concatenated onto ``lammps.log``.  Using 'grep' to extract the cohesive energies from ``lammps.log``, a JSON dictionary containing the results is created and printed as the last line of stdout.  Take note of the ``[...]`` used inside of the JSON dictionary, which are used to define the entries ``latticeconstantarray`` and ``cohesiveenergyarray``, which are themselves *arrays* of dictionaries.

.. _example2_TD_kimspec:

kimspec.yaml
^^^^^^^^^^^^
This YAML-formatted file contains metadata associated with the Test Driver. More information on these files can be found `here <https://kim-items.openkim.org/kimspec-format>`_.  This file must always be named ``kimspec.yaml``.
 
.. code-block:: yaml

    extended-id: LammpsExample2__TD_887699523131_000
    title: "LammpsExample2: compute energy-volume curve for a given lattice."
    description: "This example Test Driver illustrates the use of LAMMPS in the openkim-pipeline to compute an energy-volume curve (more
       specifically, a cohesive energy-lattice constant curve) for a given cubic lattice (fcc, bcc, sc, diamond) of a single given species.
       The curve is computed for lattice constants ranging from a_min to a_max, with most samples being about a_0 (a_min, a_max, and a_0
       are specified via stdin.  a_0 is typically approximately equal to the equilibrium lattice constant.).
       The precise scaling of sample points going from a_min to a_0 and from a_0 to a_max is specified by two separate parameters passed
       from stdin.  Please see README.txt for further details."
    notes: "Submitted by Daniel S. Karls (karl0100 |AT| umn DOT edu), University of Minnesota."
    domain: openkim.org

.. _example2_TD_makefile:

Makefile
^^^^^^^^
As there is no need to compile :ref:`example2_TD_exec`, the Makefile is uninteresting. ::

    all:
                @echo "Nothing to make"
    
    clean:
                @echo "Nothing to clean"

.. _example2_TD_lammpstemplate:

lammps.in.template
^^^^^^^^^^^^^^^^^^
This file is processed by :ref:`example2_TD_exec` using the 'sed' command line utility and the information entered on stdin through :ref:`example2_TE_stdin`.  The processed file is then written to the final LAMMPS input script which is run (``lammps.in`` in the Test Result directory).  Note that when using a KIM Model within LAMMPS, the appropriate LAMMPS 'pair_style' to use is `pair_style kim <http://lammps.sandia.gov/doc/pair_kim.html>`_. ::

    # Define looping variables
    variable loopcount loop sed_numberofspacings_string
    variable latticeconst index sed_latticeconst_string
    
    # Define unit set and class of atomic model
    units metal
    atom_style atomic
    
    # Periodic boundary conditions along all three dimensions
    boundary p p p
    
    # Create an FCC lattice with a spacing specified by the user (referred to as "a_0" in
    # README.txt) using a single conventional (orthogonal) unit cell
    lattice sed_latticetype_string ${latticeconst}
    region box block 0 1 0 1 0 1 units lattice
    create_box 1 box
    create_atoms 1 box
    mass 1 sed_mass_string
    
    # Specify which KIM Model to use
    pair_style kim LAMMPSvirial sed_model_string
    pair_coeff * * sed_species_string
    
    # Set what thermodynamic information to print to log
    thermo_style custom step atoms xlo xhi ylo yhi zlo zhi pe press pxx pyy pzz pxy pxz pyz
    thermo 10 # Print every 10 steps
    
    # Set what information to write to dump file
    dump id all custom 10 output/lammps.dump id type x y z fx fy fz
    dump_modify id format "%d %d %16.7f %16.7f %16.7f %16.7f %16.7f %16.7f"
    
    # Compute the energy and forces for this lattice spacing
    run 0
    
    # Define auxiliary variables to contain cohesive energy and equilibrium lattice constant
    variable poteng    equal "c_thermo_pe"
    variable natoms    equal "count(all)"
    variable ecohesive equal "v_poteng/v_natoms"
    
    # Output cohesive energy and equilibrium lattice constant
    print "Cohesive energy = ${ecohesive} eV/atom"
    
    # Queue next loop
    clear # Clear existing atoms, variables, and allocated memory
    next latticeconst # Increment latticeconst to next value
    next loopcount # Increment loopcount to next value
    jump SELF # Reload this input script with the new variable values

.. _example2_TE_ref:

Test
--------
We consider next a particular Test which uses the Test Driver above.  This Test computes a specific cohesive energy versus lattice constant curve for diamond Silicon.

List of files
^^^^^^^^^^^^^

    * :ref:`example2_TE_exec` - the main executable, a python script
    * :ref:`example2_TE_kimfile` - a KIM descriptor file which outlines the capabilities of the Test
    * :ref:`example2_TE_kimspec` - a file which describes the metadata associated with the Test
    * :ref:`example2_TE_makefile` - a Makefile
    * :ref:`example2_TE_stdin` - a Jinja template file to provide input on stdin
    * :ref:`example2_TE_results` - a Jinja template file for the results
    * ``README.txt`` - a file which contains a basic explanation of the Test
    * ``LICENSE.CDDL`` - a copy of the `CDDL license <http://opensource.org/licenses/CDDL-1.0>`_ 

.. _example2_TE_exec:

LammpsExample2_Si_diamond__TE_837477125670_000
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
As mentioned in Example 1, the contents of a Test's executable file can be a copy of the following standard python script whenever it is derived from a Test Driver::

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

.. _example2_TE_kimfile:

LammpsExample2_Si_diamond__TE_837477125670_000.kim
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
As always, the .kim descriptor file outlines the essential details of a Test, including the units it uses, the atomic species it supports, the neighborlist methods it contains, what information it passes to a Model, and what information it expects to receive from a Model. ::

    TEST_NAME        := LammpsExample2_Si_diamond__TE_837477125670_000
    Unit_Handling    := flexible
    Unit_length      := A
    Unit_energy      := eV
    Unit_charge      := e
    Unit_temperature := K
    Unit_time        := ps
    
    SUPPORTED_ATOM/PARTICLES_TYPES:
    Si spec 14
    
    CONVENTIONS:
    ZeroBasedLists    flag
    Neigh_BothAccess  flag
    NEIGH_PURE_H      flag
    NEIGH_PURE_F      flag
    NEIGH_RVEC_F      flag
    
    MODEL_INPUT:
    numberOfParticles            integer  none    []
    numberParticleTypes          integer  none    []
    particleTypes                integer  none    [numberOfParticles]
    coordinates                  double   length  [numberOfParticles,3]
    numberContributingParticles  integer  none    []
    get_neigh                    method   none    []
    neighObject                  pointer  none    []
    
    MODEL_OUTPUT:
    compute  method  none    []
    destroy  method  none    []
    cutoff   double  length  []
    energy   double  energy  []
    forces   double  force   [numberOfParticles,3]

.. warning:: Although a .kim descriptor file must be included with every Test, please bear in mind that this file is not explicitly used by LAMMPS, but instead only by the pipeline when determining compatible Test-Model pairings.  Rather, whenever LAMMPS is run with 'pair_style kim', it dynamically creates a .kim descriptor file for the Test which remains unseen by the user.  The contents of this .kim file depend on the details of the LAMMPS input script.  For example, the "CLUSTER" neighborlisting method is only included in this .kim file if a single processor is being used and none of the directions are periodic.  Moreover, note that LAMMPS is currently not compatible with the MI_OPBC_H or MI_OPBC_F neighborlisting methods.  The code which writes the .kim file is located inside of the ``pair_kim.cpp`` source file under ``/src/KIM/`` in the LAMMPS root directory.  An up-to-date version of ``pair_kim.cpp`` can also be viewed in the `LAMMPS git mirror <http://git.icms.temple.edu/git/>`_ by going to "tree" under "lammps-ro.git" and proceeding to ``/src/KIM/``.

.. _example2_TE_kimspec:

kimspec.yaml
^^^^^^^^^^^^
This YAML_formatted file contains metadata associated with the Test.  More information on these files can be found `here <https://kim-items.openkim.org/kimspec-format>`_.  This file must always be named ``kimspec.yaml``.

.. code-block:: yaml

    extended-id: LammpsExample2_Si_diamond__TE_837477125670_000
    test-driver: LammpsExample2__TD_887699523131_000
    title: "LammpsExample2_Si_diamond: compute energy-volume curve for diamond Silicon."
    species: Si
    description: "This example Test illustrates the use of LAMMPS in the openkim-pipeline to compute an energy vs. lattice
       constant curve for diamond Silicon.  The curve is computed for lattice constants ranging from 4.15 Angstroms
       to 7.5 Angstroms, with most lattice spacings sampled about 5.43 Angstroms."
    notes: "Submitted by Daniel S. Karls (karl0100 |AT| umn DOT edu), University of Minnesota"
    domain: openkim.org

.. _example2_TE_makefile:

Makefile
^^^^^^^^
As there is no need to compile :ref:`example2_TE_exec`, the Makefile is uninteresting. ::

    all:
                @echo "Nothing to make"
    
    clean:
                @echo "Nothing to clean"

.. _example2_TE_stdin:

pipeline.stdin.tpl
^^^^^^^^^^^^^^^^^^
This Jinja template is used to input information to :ref:`example2_TD_exec` on stdin.

::

    @< path("LammpsExample2__TD_887699523131_000") >@
    @< MODELNAME >@
    Si
    28.085
    diamond
    5.43
    4.15
    14
    7.5
    21
    5
    20

.. _example2_TE_results:

results.yaml.tpl
^^^^^^^^^^^^^^^^
This Jinja template is used to report the results of the Test.  In this case, a property named ``cohesive-energy-relation`` is reported which contains the primitives ``crystal-structure``, ``equilibrium-ensemble-nvt``, and ``cohesive-energy``.

::

    # This file was generated automatically using the openkim-pipeline `testgenie` utility
    # along with the template files found in the directory of the Test Driver (LammpsExample2__TD_887699523131_000)
    #
    ---
    crystal-structure:
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/crystal-structure
      a:
        source-unit: angstrom
        source-value:
    @[ for latticeconst in latticeconstantarray ]@
        - @<latticeconst.lattice_constant>@
    @[ endfor ]@
        table-info: cohesiveenergyversuslatticeconstant
      alpha:
        source-value: 90
        source-unit:  degrees
      b:
        source-unit:  angstrom
        source-value:
    @[ for latticeconst in latticeconstantarray ]@
        - @<latticeconst.lattice_constant>@
    @[ endfor ]@
      beta:
        source-value: 90
        source-unit:  degrees
      c:
        source-unit: angstrom
        source-value:
    @[ for latticeconst in latticeconstantarray ]@
        - @<latticeconst.lattice_constant>@
    @[ endfor ]@
      gamma:
            source-value: 90
            source-unit:  degrees
      short-name:
      - @<crystal_structure>@
      space-group: @<space_group>@
      wyckoff-site:
      - code: @<wyckoff_code>@
        fract-x:
          source-value: 0
          source-unit: 1
        fract-y:
          source-value: 0
          source-unit: 1
        fract-z:
          source-value: 0
          source-unit: 1
        set-or-measured: set
        species: @<element>@
    
    nvt:
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/equilibrium-ensemble-nvt
      temperature:
        source-value: 0
        source-unit: K
    
    cohesive-energy:
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/cohesive-energy
      source-unit: eV
      source-value:
    @[ for ecoh in cohesiveenergyarray ]@
      - @<ecoh.cohesive_energy>@
    @[ endfor ]@
      table-info: cohesiveenergyversuslatticeconstant
    
    table-info:
      cohesiveenergyversuslatticeconstant:
        dim: 1
        fields:
        - crystal-structure.a.source-value
        - cohesive-energy.source-value
        n-fields: 2
        shape:
        - @<numberofspacings>@
    
    kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:property/cohesive-energy-relation

Here, we see the use of ``for`` loops in the template which cycle over elements in the ``latticeconstantarray`` and ``cohesiveenergyarray`` entries output by :ref:`example2_TD_exec`.  The actual "curve" of cohesive energy versus lattice constant is defined using the ``table-info`` key.  In this case, ``table-info`` is listed alongside the array of values for ``a`` under the ``crystal-structure`` primitive and alongside the array of values under the ``cohesive-energy`` primitive.  The ``table-info`` entry at the bottom of the file tells the pipeline how to construct the "table," i.e. the pairing of the array of lattice constants with the array of cohesive energies.  Each of the ``n-fields`` arrays of length ``shape`` consists of ``dim``-dimensional data.  The values of each array are assumed to correspond in sequence, e.g. the the first element of the lattice constant array is paired with the first entry of the cohesive energy array, and so on.

.. _example2_calc_ref:

Example Calculation
-------------------
We can run this Test against one of the Models for Silicon in the OpenKIM repository, such as ``EDIP_BOP_Bazant_Kaxiras_Si__MO_958932894036_000``.  We once again use ``pipeline_runpair``::

    pipeline_runpair LammpsExample2_Si_diamond__TE_837477125670_000 EDIP_BOP_Bazant_Kaxiras_Si__MO_958932894036_000

which produces output similar to ::

    2014-01-28 21:40:21,532 - INFO - pipeline.development - Running combination <<Test(LammpsExample2_Si_diamond__TE_837477125670_000)>, <Model(EDIP_BOP_Bazant_Kaxiras_Si__MO_958932894036_000)>
    2014-01-28 21:40:21,571 - INFO - pipeline.compute - running <Test(LammpsExample2_Si_diamond__TE_837477125670_000)> with <Model(EDIP_BOP_Bazant_Kaxiras_Si__MO_958932894036_000)>
    2014-01-28 21:40:21,575 - INFO - pipeline.template - attempting to process '/home/openkim/openkim-repository/te/LammpsExample2_Si_diamond_runningc9d4b5f0-8864-11e3-8118-4005d10d911c__TE_837477125670_000/pipeline.stdin.tpl' for ('LammpsExample2_Si_diamond__TE_837477125670_000','EDIP_BOP_Bazant_Kaxiras_Si__MO_958932894036_000')
    2014-01-28 21:40:21,585 - INFO - pipeline.compute - launching run...
    2014-01-28 21:40:22,007 - INFO - pipeline.compute - Run completed in 0.42205309867858887 seconds
    2014-01-28 21:40:22,789 - INFO - pipeline.compute - Copying the contents of /home/openkim/openkim-repository/te/LammpsExample2_Si_diamond_runningc9d4b5f0-8864-11e3-8118-4005d10d911c__TE_837477125670_000/output to /home/openkim/openkim-repository/tr/c9d4b5f0-8864-11e3-8118-4005d10d911c

In this case, the last line of the output indicates that the results of the calculation have been copied to ``/home/openkim/openkim-repository/tr/c9d4b5f0-8864-11e3-8118-4005d10d911c``.  Examining ``pipeline.stdout``, we can see the JSON dictionary printed by the Test Driver::

    Please enter a valid KIM Model extended-ID:
    Please enter the species symbol (e.g. Si, Au, Al, etc.):
    Please enter the atomic mass of the species (g/mol):
    Please enter the lattice type (bcc, fcc, sc, or diamond):
    Please specify a lattice constant (referred to as a_0 below) about which the energy will be computed (This will usually be the equilibrium lattice constant.  Most of the volumes sampled will be about this lattice constant.):
    Please specify the smallest lattice spacing (referred to as a_min below) at which to compute the energy:
    Please enter the number of sample lattice spacings to compute which are >= a_min and < a_0 (one of these sample lattice spacings will be equal to a_min):
    Please specify the largest lattice spacing (referred to as a_max below) at which to compute the energy:
    Please enter the number of sample lattice spacings to compute which are > a_0 and <= a_max (one of these sample lattice spacings will be equal to a_max):
    Please enter a value of the lower sample spacing parameter (see README.txt for more details):
    Please enter a value of the upper sample spacing parameter (see README.txt for more details):
    { "crystal_structure": "diamond",  "element": "Si", "wyckoff_code": "8a", "space_group": "Fd-3m", "numberofspacings": "36",
    "latticeconstantarray": [ {"lattice_constant": "4.150000"}, {"lattice_constant": "4.349873"}, {"lattice_constant": "4.509468"},
    {"lattice_constant": "4.642327"}, {"lattice_constant": "4.756137"}, {"lattice_constant": "4.855680"}, {"lattice_constant": "4.944139"},
    {"lattice_constant": "5.023736"}, {"lattice_constant": "5.096087"}, {"lattice_constant": "5.162401"}, {"lattice_constant": "5.223608"},
    {"lattice_constant": "5.280440"}, {"lattice_constant": "5.333481"}, {"lattice_constant": "5.383204"}, {"lattice_constant": "5.430000"},
    {"lattice_constant": "5.461988"}, {"lattice_constant": "5.495529"}, {"lattice_constant": "5.530781"}, {"lattice_constant": "5.567929"},
    {"lattice_constant": "5.607188"}, {"lattice_constant": "5.648813"}, {"lattice_constant": "5.693107"}, {"lattice_constant": "5.740436"},
    {"lattice_constant": "5.791247"}, {"lattice_constant": "5.846093"}, {"lattice_constant": "5.905670"}, {"lattice_constant": "5.970873"},
    {"lattice_constant": "6.042876"}, {"lattice_constant": "6.123265"}, {"lattice_constant": "6.214252"}, {"lattice_constant": "6.319063"},
    {"lattice_constant": "6.442666"}, {"lattice_constant": "6.593302"}, {"lattice_constant": "6.786204"}, {"lattice_constant": "7.054760"},
    {"lattice_constant": "7.500000"}], "cohesiveenergyarray": [ {"cohesive_energy": "-2.08463"}, {"cohesive_energy": "2.57501"}, {"cohesive_energy": "3.13935"},
    {"cohesive_energy": "3.53906"}, {"cohesive_energy": "3.83239"}, {"cohesive_energy": "4.05241"}, {"cohesive_energy": "4.21949"}, {"cohesive_energy": "4.34691"},
    {"cohesive_energy": "4.44379"}, {"cohesive_energy": "4.51658"}, {"cohesive_energy": "4.57001"}, {"cohesive_energy": "4.60762"}, {"cohesive_energy": "4.63215"},
    {"cohesive_energy": "4.6457"}, {"cohesive_energy": "4.64995"}, {"cohesive_energy": "4.64805"}, {"cohesive_energy": "4.64178"}, {"cohesive_energy": "4.63042"},
    {"cohesive_energy": "4.61306"}, {"cohesive_energy": "4.58861"}, {"cohesive_energy": "4.55569"}, {"cohesive_energy": "4.51258"}, {"cohesive_energy": "4.45711"},
    {"cohesive_energy": "4.38644"}, {"cohesive_energy": "4.29688"}, {"cohesive_energy": "4.1835"}, {"cohesive_energy": "4.04013"}, {"cohesive_energy": "3.86195"},
    {"cohesive_energy": "3.64285"}, {"cohesive_energy": "3.37092"}, {"cohesive_energy": "3.02077"}, {"cohesive_energy": "2.54026"}, {"cohesive_energy": "1.82299"},
    {"cohesive_energy": "0.714214"}, {"cohesive_energy": "0.0031393"}, {"cohesive_energy": "0"}]}


The first things reported are ``crystal_structure``, ``element``, ``wyckoff_code``, ``space-group``, and ``numberofspacings``.  After this, ``latticeconstantarray``, which consists of 36 individual dictionary entries that contain the key ``lattice_constant``, is given.  Finally, ``cohesiveenergyarray`` is defined.  In :ref:`example2_TE_results`, the code snippets

::

    @[ for latticeconst in latticeconstantarray ]@
        - @<latticeconst.lattice_constant>@
    @[ endfor ]@

and

::

    @[ for ecoh in cohesiveenergyarray ]@
      - @<ecoh.cohesive_energy>@
    @[ endfor ]@

first assign a local, dummy name to represent an entry in the relevant arrays (``latticeconst`` for ``latticeconstantarray``, and ``ecoh`` for ``cohesiveenergyarray``).  The actual values of each entry are then accessed using the exact key names that were specified in :ref:`example2_TD_exec`, ``lattice_constant`` and ``cohesive_energy``, respectively.


Finally, the ``results.yaml`` file looks like::

    ---
    cohesive-energy:
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/cohesive-energy
      si-unit: kg m^2 / s^2
      si-value:
      - -3.3399451e-19
      - 4.1256204e-19
      - 5.0297927e-19
      - 5.6701986e-19
      - 6.1401651e-19
      - 6.4926759e-19
      - 6.7603676e-19
      - 6.9645169e-19
      - 7.1197357e-19
      - 7.2363582e-19
      - 7.3219625e-19
      - 7.3822203e-19
      - 7.4215217e-19
      - 7.4432312e-19
      - 7.4500404e-19
      - 7.4469963e-19
      - 7.4369507e-19
      - 7.4187499e-19
      - 7.3909361e-19
      - 7.3517629e-19
      - 7.2990193e-19
      - 7.2299495e-19
      - 7.1410767e-19
      - 7.0278509e-19
      - 6.88436e-19
      - 6.7027052e-19
      - 6.4730012e-19
      - 6.1875254e-19
      - 5.8364885e-19
      - 5.4008087e-19
      - 4.8398066e-19
      - 4.0699448e-19
      - 2.9207517e-19
      - 1.1442969e-19
      - 5.0297126e-22
      - 0.0
      source-unit: eV
      source-value:
      - -2.08463
      - 2.57501
      - 3.13935
      - 3.53906
      - 3.83239
      - 4.05241
      - 4.21949
      - 4.34691
      - 4.44379
      - 4.51658
      - 4.57001
      - 4.60762
      - 4.63215
      - 4.6457
      - 4.64995
      - 4.64805
      - 4.64178
      - 4.63042
      - 4.61306
      - 4.58861
      - 4.55569
      - 4.51258
      - 4.45711
      - 4.38644
      - 4.29688
      - 4.1835
      - 4.04013
      - 3.86195
      - 3.64285
      - 3.37092
      - 3.02077
      - 2.54026
      - 1.82299
      - 0.714214
      - 0.0031393
      - 0
      table-info: cohesiveenergyversuslatticeconstant
    crystal-structure:
      a:
        si-unit: m
        si-value:
        - 4.15e-10
        - 4.349873e-10
        - 4.509468e-10
        - 4.642327e-10
        - 4.756137e-10
        - 4.85568e-10
        - 4.944139e-10
        - 5.023736e-10
        - 5.096087e-10
        - 5.162401e-10
        - 5.223608e-10
        - 5.28044e-10
        - 5.333481e-10
        - 5.383204e-10
        - 5.43e-10
        - 5.461988e-10
        - 5.495529e-10
        - 5.530781e-10
        - 5.567929e-10
        - 5.607188e-10
        - 5.648813e-10
        - 5.693107e-10
        - 5.740436e-10
        - 5.791247e-10
        - 5.846093e-10
        - 5.90567e-10
        - 5.970873e-10
        - 6.042876e-10
        - 6.123265e-10
        - 6.214252e-10
        - 6.319063e-10
        - 6.442666e-10
        - 6.593302e-10
        - 6.786204e-10
        - 7.05476e-10
        - 7.5e-10
        source-unit: angstrom
        source-value:
        - 4.15
        - 4.349873
        - 4.509468
        - 4.642327
        - 4.756137
        - 4.85568
        - 4.944139
        - 5.023736
        - 5.096087
        - 5.162401
        - 5.223608
        - 5.28044
        - 5.333481
        - 5.383204
        - 5.43
        - 5.461988
        - 5.495529
        - 5.530781
        - 5.567929
        - 5.607188
        - 5.648813
        - 5.693107
        - 5.740436
        - 5.791247
        - 5.846093
        - 5.90567
        - 5.970873
        - 6.042876
        - 6.123265
        - 6.214252
        - 6.319063
        - 6.442666
        - 6.593302
        - 6.786204
        - 7.05476
        - 7.5
        table-info: cohesiveenergyversuslatticeconstant
      alpha:
        si-unit: radian
        si-value: 1.5707963
        source-unit: degrees
        source-value: 90
      b:
        si-unit: m
        si-value:
        - 4.15e-10
        - 4.349873e-10
        - 4.509468e-10
        - 4.642327e-10
        - 4.756137e-10
        - 4.85568e-10
        - 4.944139e-10
        - 5.023736e-10
        - 5.096087e-10
        - 5.162401e-10
        - 5.223608e-10
        - 5.28044e-10
        - 5.333481e-10
        - 5.383204e-10
        - 5.43e-10
        - 5.461988e-10
        - 5.495529e-10
        - 5.530781e-10
        - 5.567929e-10
        - 5.607188e-10
        - 5.648813e-10
        - 5.693107e-10
        - 5.740436e-10
        - 5.791247e-10
        - 5.846093e-10
        - 5.90567e-10
        - 5.970873e-10
        - 6.042876e-10
        - 6.123265e-10
        - 6.214252e-10
        - 6.319063e-10
        - 6.442666e-10
        - 6.593302e-10
        - 6.786204e-10
        - 7.05476e-10
        - 7.5e-10
        source-unit: angstrom
        source-value:
        - 4.15
        - 4.349873
        - 4.509468
        - 4.642327
        - 4.756137
        - 4.85568
        - 4.944139
        - 5.023736
        - 5.096087
        - 5.162401
        - 5.223608
        - 5.28044
        - 5.333481
        - 5.383204
        - 5.43
        - 5.461988
        - 5.495529
        - 5.530781
        - 5.567929
        - 5.607188
        - 5.648813
        - 5.693107
        - 5.740436
        - 5.791247
        - 5.846093
        - 5.90567
        - 5.970873
        - 6.042876
        - 6.123265
        - 6.214252
        - 6.319063
        - 6.442666
        - 6.593302
        - 6.786204
        - 7.05476
        - 7.5
      beta:
        si-unit: radian
        si-value: 1.5707963
        source-unit: degrees
        source-value: 90
      c:
        si-unit: m
        si-value:
        - 4.15e-10
        - 4.349873e-10
        - 4.509468e-10
        - 4.642327e-10
        - 4.756137e-10
        - 4.85568e-10
        - 4.944139e-10
        - 5.023736e-10
        - 5.096087e-10
        - 5.162401e-10
        - 5.223608e-10
        - 5.28044e-10
        - 5.333481e-10
        - 5.383204e-10
        - 5.43e-10
        - 5.461988e-10
        - 5.495529e-10
        - 5.530781e-10
        - 5.567929e-10
        - 5.607188e-10
        - 5.648813e-10
        - 5.693107e-10
        - 5.740436e-10
        - 5.791247e-10
        - 5.846093e-10
        - 5.90567e-10
        - 5.970873e-10
        - 6.042876e-10
        - 6.123265e-10
        - 6.214252e-10
        - 6.319063e-10
        - 6.442666e-10
        - 6.593302e-10
        - 6.786204e-10
        - 7.05476e-10
        - 7.5e-10
        source-unit: angstrom
        source-value:
        - 4.15
        - 4.349873
        - 4.509468
        - 4.642327
        - 4.756137
        - 4.85568
        - 4.944139
        - 5.023736
        - 5.096087
        - 5.162401
        - 5.223608
        - 5.28044
        - 5.333481
        - 5.383204
        - 5.43
        - 5.461988
        - 5.495529
        - 5.530781
        - 5.567929
        - 5.607188
        - 5.648813
        - 5.693107
        - 5.740436
        - 5.791247
        - 5.846093
        - 5.90567
        - 5.970873
        - 6.042876
        - 6.123265
        - 6.214252
        - 6.319063
        - 6.442666
        - 6.593302
        - 6.786204
        - 7.05476
        - 7.5
      gamma:
        si-unit: radian
        si-value: 1.5707963
        source-unit: degrees
        source-value: 90
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/crystal-structure
      short-name:
      - diamond
      space-group: Fd-3m
      wyckoff-site:
      - code: 8a
        fract-x:
          si-unit: '1'
          si-value: 0.0
          source-unit: 1
          source-value: 0
        fract-y:
          si-unit: '1'
          si-value: 0.0
          source-unit: 1
          source-value: 0
        fract-z:
          si-unit: '1'
          si-value: 0.0
          source-unit: 1
          source-value: 0
        set-or-measured: set
        species: Si
    kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:property/cohesive-energy-relation
    nvt:
      kim-namespace: tag:staff@noreply.openkim.org,2013-08-03:primitive/equilibrium-ensemble-nvt
      temperature:
        si-unit: K
        si-value: 0.0
        source-unit: K
        source-value: 0
    table-info:
      cohesiveenergyversuslatticeconstant:
        dim: 1
        fields:
        - crystal-structure.a.source-value
        - cohesive-energy.source-value
        n-fields: 2
        shape:
        - 36

.. note:: Another Test derived from this Test Driver, LammpsExample2_Ar_fcc__TE_778998786610_000, can be found in the source archive of these example Tests.
.. note:: The ``testgenie`` utility included on the OpenKIM Virtual Machine was used to generate the Tests LammpsExample2_Si_diamond__TE_837477125670_000 and LammpsExample2_Ar_fcc__TE_778998786610_000.  This utility operates using a file named ``test_generator.json`` in the Test Driver directory and the template files found in ``test_template/``.  To generate these two Tests, enter the LammpsExample2__TD_887699523131_000 directory and issue, for example, the command ``testgenie --destination ~/openkim-repository/te/ LammpsExample2__TD_887699523131_000``.  For more information on ``testgenie``, enter the command ``testgenie --h``.
