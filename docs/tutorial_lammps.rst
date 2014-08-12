Example tests - LAMMPS
**********************

We consider here the use of the `LAMMPS Molecular Dynamics Simulator <http://lammps.sandia.gov/>`_ in constructing Tests within the OpenKIM Pipeline (hereafter, "the pipeline").  This process essentially amounts to the following steps:

#. Creating a LAMMPS input script which is accessed by the Test executable
#. Invoking LAMMPS from the Test executable
#. Parsing the LAMMPS output for the quantities of interest
#. Post-processing the quantities of interest, if necessary, and reporting the results of the Test

Although not strictly necessary in general, both of the Tests included in this tutorial have been constructed to make use of Test Drivers for the purpose of demonstration.  In order to download these Tests and their Test Drivers, as well as the Model we'll use and its Model Driver, log into the VM and issue the following commands:

.. _install_ref:
.. code-block:: bash

    kimitems install LammpsExample__TE_565333229701_001
    kimitems install LammpsExample__TD_567444853524_001
    kimitems install LammpsExample2_fcc_Ar__TE_778998786610_001
    kimitems install LammpsExample2__TD_887699523131_001
    kimitems install Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_001
    kimitems install Pair_Lennard_Jones_Shifted__MD_498634107543_001

.. #### Give link to :ref:`testdev` once it's updated.

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
-----------
Let's begin by looking at the Test Driver for the first example.  This Test Driver is constructed to compute the cohesive energy and equilibrium lattice constant of an fcc Argon lattice.  Each Test which uses this Test Driver can supply its own initial guess at the equilibrium lattice spacing.

List of files
^^^^^^^^^^^^^

    * :ref:`example1_TD_kimspec` - a file which describes the metadata associated with the Test Driver
    * :ref:`example1_TD_resultstemplate` - an EDN-formatted (see `About the EDN data format`_) template which the Test Driver processes with \`sed`
    * :ref:`example1_TD_lammpstemplate` - a LAMMPS input script template which the Test Driver processes with \`sed`
    * :ref:`example1_TD_exec` - the main executable, a bash script
    * :ref:`example1_TD_makefile` - a Makefile
    * ``README.txt`` - a file which contains a basic explanation of the Test Driver
    * ``LICENSE.CDDL`` - a copy of the `CDDL license <http://opensource.org/licenses/CDDL-1.0>`_

.. _example1_TD_kimspec:

kimspec.edn
^^^^^^^^^^^

This EDN-formatted file (see `About the EDN data format`_) contains metadata associated with the Test Driver.  More information on these files can be found `here <https://kim-items.openkim.org/kimspec-format>`_. This file must always be named ``kimspec.edn``.

.. code-block:: clojure

    {
      "description" "This example Test Driver illustrates the use of LAMMPS in the openkim-pipeline
    to compute the equilibrium lattice spacing and cohesive energy of fcc Argon using
    Polak-Ribiere conjugate gradient minimization in LAMMPS and an initial guess at
    the equilibrium lattice spacing supplied by the user through pipeline.stdin.tpl."
      "domain" "openkim.org"
      "executables" [ "runner" ]
      "extended-id" "LammpsExample__TD_567444853524_001"
      "kim-api-version" "1.6"
      "title" "LammpsExample: cohesive energy and equilibrium lattice constant of fcc Argon"
      "pipeline-api-version" "1.0"
      "properties" ["tag:staff@noreply.openkim.org,2014-04-15:property/cohesive-potential-energy-cubic-crystal"]
    }

.. _example1_TD_resultstemplate:

results.edn.tpl
^^^^^^^^^^^^^^^
This file is not standardized as part of KIM, but rather just a template created for convenience.  However, note that whichever method you choose to generate your results (whether via a template or printing them directly), your Test must eventually produce a valid edn document named ``results.edn`` which conforms to the `KIM Properties Framework`_.  In this case, a suitable Property Definition to have our Test report is `cohesive-potential-energy-cubic-crystal`_.  By looking at the KIM Items page of this property, we can see that we should report the lattice constant in the key ``a`` and the cohesive energy in the ``cohesive-potential-energy`` key.  We can already fill in ``short-name``, ``species``, ``basis-atom-coordinates``, ``space-group``, ``wyckoff-multiplicity-and-letter``, and ``wyckoff-cordinates`` in the template since the Test Driver is designed to always do the computation with a single conventional fcc cell of four argon atoms.  Moreover, since we're using "`units metal`_" in the lammps input script, we already know that the values of lattice constant and cohesive energy we parse from the LAMMPS output will be in units of angstroms and eV, respectively.

.. code-block:: clojure

    {
      "property-id" "tag:staff@noreply.openkim.org,2014-04-15:property/cohesive-potential-energy-cubic-crystal"
      "instance-id" 1
      "short-name" {
        "source-value" [ "fcc Argon" ]
      }
      "species" {
        "source-value" [
          "Ar"
          "Ar"
          "Ar"
          "Ar"
        ]
      }
      "a" {
        "source-value" _LATCONST_
        "source-unit" "angstrom"
      }
      "basis-atom-coordinates" {
        "source-value" [
          [   0    0    0 ]
          [   0  0.5  0.5 ]
          [ 0.5    0  0.5 ]
          [ 0.5  0.5    0 ]
        ]
      }
      "space-group" {
        "source-value" "Fm-3m"
      }
      "wyckoff-multiplicity-and-letter" {
        "source-value" [ "4a" ]
      }
      "wyckoff-coordinates" {
        "source-value" [ [ 0 0 0 ] ]
      }
      "cohesive-potential-energy" {
        "source-value" _ECOHESIVE_
        "source-unit" "eV"
      }
    }

.. warning:: LAMMPS does not always use "derived" sets of units, as the KIM API does.  In this example, LAMMPS uses "`units metal`_" as instructed to in :ref:`example1_TD_lammpstemplate`.  In this system of units, for example, pressure is reported in bars rather than eV/Angstrom^3 even though the unit for energy is eV and the unit for length is Angstroms.  Therefore, one should pay attention to what units are actually being reported.  However, this is easy to resolve, since any units defined within `GNU Units <http://www.gnu.org/software/units/>`_ can be specified as the ``source-unit`` field in the final ``results.edn`` file that a Test generates.

.. _example1_TD_lammpstemplate:

lammps.in.template
^^^^^^^^^^^^^^^^^^
This file is processed by :ref:`example1_TD_exec` using the \`sed` command line utility and the information entered on stdin through :ref:`example1_TE_stdin`.  The processed file is then written to the final LAMMPS input script which is run (``lammps.in`` in the Test Result directory). Note that when using a KIM Model within LAMMPS, the appropriate LAMMPS 'pair_style' to use is `pair_style kim <http://lammps.sandia.gov/doc/pair_kim.html>`_.

::

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

.. _example1_TD_exec:

runner
^^^^^^
.. code-block:: bash

    #!/usr/bin/env bash

    # Author: Daniel S. Karls (karl0100 |AT| umn DOT edu), University of Minnesota
    # Date: 8/04/2014

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

    #JSONresults="{ \"latticeconstant\": \"$latticeconstant\", \"cohesiveenergy\": \"$ecohesive\", \"finalpressure\": \"$finalpressure\" }"
    sed "s/_LATCONST_/${latticeconstant}/" ""$thisdir"/results.edn.tpl" > output/results.edn
    sed -i "s/_ECOHESIVE_/${ecohesive}/" output/results.edn
    sed -i "s/_PFINAL_/${finalpressure}/" output/results.edn

We begin by reading the Model name and the initial lattice constant from stdin.  The instantiations of these are contained in the :ref:`example1_TE_stdin` file of the Test itself.  The Model name and initial lattice constant are then used to replace the corresponding placeholder strings in :ref:`example1_TD_lammpstemplate` to create a functioning LAMMPS input script, ``lammps.in``, in the Test Result directory (``output/``).  LAMMPS is then called using ``lammps.in`` as an input script and the resulting output is redirected to a file named ``lammps.log`` in the Test Result directory.  After the quantities of interest in the LAMMPS log file are parsed, \`sed` is used to replace the relevant placeholder strings in :ref:`example1_TD_resultstemplate` and yield a file named ``results.edn`` in the Test Result directory.

This executable of a Test Driver must always be named ``runner``.

.. _example1_TD_makefile:

Makefile
^^^^^^^^
As there is no need to compile :ref:`example1_TD_exec` since it is a bash script, the Makefile is uninteresting.  In fact, it could just as well have been omitted since Makefiles are not required by the pipeline if no compilation is needed.

::

    all:
                @echo "Nothing to make"

    clean:
                @echo "Nothing to clean"

.. _example1_TE_ref:

Test
--------
Next, we inspect a Test which uses the above Test Driver.  In this case, this Test corresponds to one particular initial guess at the lattice constant, 5.3 Angstroms.

.. _example1_TE_listoffiles:

List of files
^^^^^^^^^^^^^

    * :ref:`example1_TE_kimspec` - a file which describes the metadata associated with the Test
    * :ref:`example1_TE_kimfile` - a KIM descriptor file which outlines the capabilities of the Test
    * :ref:`example1_TE_stdin` - a `Jinja`_-formatted template file processed by the pipeline used to provide input to the Test
    * :ref:`example1_TE_exec` - the main executable, a python script
    * :ref:`example1_TE_makefile` - a Makefile
    * ``README.txt`` - a documentation file which contains a basic explanation of the Test
    * ``LICENSE.CDDL`` - a copy of the `CDDL license <http://opensource.org/licenses/CDDL-1.0>`_

.. _example1_TE_kimspec:

kimspec.edn
^^^^^^^^^^^
This EDN-formatted file (see `About the EDN data format`_) contains metadata associated with the Test.  More information on these files can be found `here <https://kim-items.openkim.org/kimspec-format>`_. This file must always be named ``kimspec.edn``.

.. code-block:: clojure

    {
      "description" "This example Test illustrates the use of LAMMPS in the openkim-pipeline to compute
      the cohesive energy of fcc Argon using conjugate gradient minimization with an initial
      guess of 5.3 Angstroms for the equilibrium lattice constant."
      "domain" "openkim.org"
      "executables" [ "runner" ]
      "extended-id" "LammpsExample__TE_565333229701_001"
      "kim-api-version" "1.6"
      "species" "Ar"
      "test-driver" "LammpsExample__TD_567444853524_001"
      "title" "LammpsExample: cohesive energy and equilibrium lattice constant of fcc Argon"
      "pipeline-api-version" "1.0"
    }



.. _example1_TE_kimfile:

descriptor.kim
^^^^^^^^^^^^^^
The .kim descriptor file outlines the operational parameters of the Test, including the units it uses, the atomic species it supports, the neighborlist methods it contains, what information it passes to a Model, and what information it expects to receive from a Model.  The name of this file should be ``descriptor.kim``.  For more information on KIM descriptor files, you can view the relevant part of the KIM API standard `here <https://raw.githubusercontent.com/openkim/kim-api/master/src/standard.kim>`_.

::

    TEST_NAME        := LammpsExample__TE_565333229701_001
    KIM_API_Version  := 1.6.0
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
    NEIGH_RVEC_H      flag
    NEIGH_RVEC_F      flag

    MODEL_INPUT:
    numberOfParticles            integer  none    []
    numberOfSpecies              integer  none    []
    particleSpecies              integer  none    [numberOfParticles]
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

.. _example1_TE_stdin:

pipeline.stdin.tpl
^^^^^^^^^^^^^^^^^^
This `Jinja`_ template file is used to input information to the Test (or its Test Driver, in this case) on stdin.  Whatever is inside of ``@<...>@`` is interpreted by the pipeline as python code (the pipeline is written in python) which evaluates to a variable.  Code blocks are also possible with ``@[...]@``.  One subtlety is that when a Test uses a Test Driver, the first line in this file should contain an evaluation of the path of the Test Driver's executable.

Here, we begin by specifying the path of the Test Driver.  We then use ``@< MODELNAME >@``, which the pipeline will automatically replace at run-time with the extended KIM ID of the Model being run against the Test.  Finally, the initial guess of 5.3 Angstroms for the equilibrium lattice constant is fed to the Test Driver.

.. code-block:: jinja

    @< path("LammpsExample__TD_567444853524_001") >@
    @< MODELNAME >@
    5.3

This file must always be named ``pipeline.stdin.tpl``.

.. #### UNCOMMENT ONCE PIPELINE DOCS ARE UPDATED Further explanation of these files can be found :ref:`here <pipelineindocs>`.

.. _example1_TE_exec:

runner
^^^^^^
In the case where a Test uses a Test Driver, the contents of its executable file can be a copy of the following standard python script:

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

which simply reads input on stdin and calls the executable of the associated Test Driver.  As with the Test Driver, the name of this file must be ``runner``.

.. _example1_TE_makefile:

Makefile
^^^^^^^^
As there is no need to compile :ref:`example1_TE_exec`, the Makefile is uninteresting. ::

    all:
                @echo "Nothing to make"

    clean:
                @echo "Nothing to clean"

.. _example1_calc_ref:

Example Calculation
-------------------
To verify that the Test Driver and Test above work, let's try running the Test against the Model that we :ref:`downloaded earlier <install_ref>`, ``Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_001`` (`click here`_ to view its KIM Items page).  In order to run a specific Test-Model pair, the pipeline provides a utility named ``pipeline_runpair`` which can be invoked in the following manner::

    pipeline_runpair LammpsExample__TE_565333229701_001 Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_001

which yields as output something similar to the following

::

    2014-08-09 02:36:06,806 - INFO - pipeline.development - Running combination <<Test(LammpsExample__TE_565333229701_001)>,
    <Model(Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_001)>
    2014-08-09 02:36:13,983 - INFO - pipeline.compute - running <Test(LammpsExample__TE_565333229701_001)> with
    <Model(Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_001)>
    2014-08-09 02:36:13,993 - INFO - pipeline.compute - launching run...
    2014-08-09 02:36:14,161 - INFO - pipeline.compute - Run completed in 0.1679060459136963 seconds
    2014-08-09 02:36:14,266 - INFO - pipeline.compute - Copying the contents of /home/openkim/openkim-repository/te/LammpsExample_r
    unningee6a7cee-1f6d-11e4-b3b3-41cabcba9ab3__TE_565333229701_001/output to /home/openkim/openkim-repository/tr/ee6a7cee-1f6d-11e
    4-b3b3-41cabcba9ab3

In this case, the last line of the output indicates that the results of the calculation have been copied to ``/home/openkim/openkim-repository/tr/ee6a7cee-1f6d-11e4-b3b3-41cabcba9ab3/``.  Let's go to this folder and inspect its contents:

::

    ~/openkim-repository/tr/ee6a7cee-1f6d-11e4-b3b3-41cabcba9ab3/
    ├── kim.log - log file created by the KIM API
    ├── kimspec.edn - metadata for the Test Result created by the pipeline
    ├── lammps.dump - LAMMPS dump file
    ├── lammps.in - final input script that was fed to LAMMPS
    ├── lammps.log - log file created by LAMMPS
    ├── pipelinespec.edn - metadata about the run created by the pipeline
    ├── pipeline.stderr - stderr output from the run
    ├── pipeline.stdin - final stdin that was fed to the run
    ├── pipeline.stdout - stdout output from the run.  The LAMMPS output log can be found here.
    └── results.edn - final results file output by the test

As previously mentioned, every OpenKIM Test must create an EDN-formatted file named ``results.edn`` which conforms to the `KIM Properties Framework`_.  Below, we see that the ``results.edn`` for this Test contains an instance of the ``cohesive-potential-energy-cubic-crystal`` Property Definition, as prescribed in :ref:`example1_TD_resultstemplate`.

.. code-block:: clojure

    {
        "short-name" {
            "source-value" [
                "fcc Argon"
            ]
        }
        "a" {
            "si-unit" "m"
            "source-unit" "angstrom"
            "si-value" 5.24859e-10
            "source-value" 5.24859000000002
        }
        "wyckoff-multiplicity-and-letter" {
            "source-value" [
                "4a"
            ]
        }
        "property-id" "tag:staff@noreply.openkim.org,2014-04-15:property/cohesive-potential-energy-cubic-crystal"
        "space-group" {
            "source-value" "Fm-3m"
        }
        "cohesive-potential-energy" {
            "si-unit" "kg m^2 / s^2"
            "source-unit" "eV"
            "si-value" 1.3859709e-20
            "source-value" 0.0865055077405508
        }
        "basis-atom-coordinates" {
            "source-value" [
                [
                    0
                    0
                    0
                ]
                [
                    0
                    0.5
                    0.5
                ]
                [
                    0.5
                    0
                    0.5
                ]
                [
                    0.5
                    0.5
                    0
                ]
            ]
        }
        "wyckoff-coordinates" {
            "source-value" [
                [
                    0
                    0
                    0
                ]
            ]
        }
        "species" {
            "source-value" [
                "Ar"
                "Ar"
                "Ar"
                "Ar"
            ]
        }
        "instance-id" 1
    }

where one can notice that the pipeline automatically creates and populate the ``si-unit`` and ``si-value`` fields for numerical values.  Looking at the above, we can see that the resulting lattice constant from our Test is ``5.24859000000002`` angstroms and the corresponding cohesive potential energy is ``0.0865055077405508`` eV.

.. For comparison, we can try to query the openkim pipeline for any other Test Results for ``cohesive-potential-energy-cubic-crystal`` which ran against ``Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_001`` and contain "fcc" in the ``short-name`` key:

.. note:: The ``inplace`` flag can be placed after the Model name when invoking ``pipeline_runpair`` in order to redirect the test results to a directory named ``output`` inside of the Test directory.
.. note:: The ``pipeline_runmatches`` command can be used to attempt to run a Test against all Models whose .kim descriptor files indicate they are compatible with the Test.

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
-----------

This Test Driver is constructed to compute a cohesive energy versus lattice constant "curve" for a cubic lattice of a given species.  The lattice constants for which the cohesive energy is computed are specified by a set of parameters given by the user.

.. _example2_TD_listoffiles:

List of files
^^^^^^^^^^^^^

    * :ref:`example2_TD_kimspec` - a file which describes the metadata associated with the Test Driver
    * :ref:`example2_TD_resultstemplate` - an EDN-formatted (see `About the EDN data format`_) template which the Test Driver processes with \`sed`
    * :ref:`example2_TD_lammpstemplate` - a LAMMPS input script template which the Test Driver processes with \`sed`
    * :ref:`example2_TD_exec` - the main executable, a bash script
    * :ref:`example2_TD_makefile` - a Makefile
    * ``README.txt`` - a file which contains a basic explanation of the Test Driver
    * ``LICENSE.CDDL`` - a copy of the `CDDL license <http://opensource.org/licenses/CDDL-1.0>`_
    * ``test_generator.json`` - a file used by ``testgenie`` to generate Tests from this Test Driver
    * ``test_template/`` - a directory containing template files used by ``testgenie`` to generate Tests from this Test Driver

.. _example2_TD_kimspec:

kimspec.edn
^^^^^^^^^^^

This EDN-formatted file (see `About the EDN data format`_) contains metadata associated with the Test Driver.  More information on these files can be found `here <https://kim-items.openkim.org/kimspec-format>`_. This file must always be named ``kimspec.edn``.

.. code-block:: clojure

    {
      "description" "This example Test Driver illustrates the use of LAMMPS in the openkim-pipeline
      to compute an energy-volume curve (more specifically, a cohesive energy-lattice
      constant curve) for a given cubic lattice (fcc, bcc, sc, diamond) of a single given
      species. The curve is computed for lattice constants ranging from a_min to a_max,
      with most samples being about a_0 (a_min, a_max, and a_0 are specified via stdin.
      a_0 is typically approximately equal to the equilibrium lattice constant.). The precise
      scaling of sample points going from a_min to a_0 and from a_0 to a_max is specified
      by two separate parameters passed from stdin.  Please see README.txt for further
      details."
      "domain" "openkim.org"
      "executables" [ "runner" "test_template/template_" ]
      "extended-id" "LammpsExample2__TD_887699523131_001"
      "kim-api-version" "1.6"
      "title" "LammpsExample2: energy-volume curve for monoatomic cubic lattice"
      "pipeline-api-version" "1.0"
      "properties" ["tag:staff@noreply.openkim.org,2014-04-15:property/cohesive-energy-relation-cubic-crystal"]
    }

.. _example2_TD_resultstemplate:

results.edn.tpl
^^^^^^^^^^^^^^^

As in the first example, the Test Driver contains a template which all of its Tests use to report their results.  As before, we caution that a Test must always eventually produce a file named ``results.edn`` by some means.  In the case of this Test Driver, a property named `cohesive-energy-relation-cubic-crystal`_ exists which captures exactly the information we need.  Again, we use "`units metal`_" in LAMMPS so that the values we directly parse for the energy will be in eV (and we define the lattice spacings to be in units of Angstroms).

.. Add a link here to documentation which points to how users can define and submit their own properties

.. code-block:: clojure

    {
      "property-id" "tag:staff@noreply.openkim.org,2014-04-15:property/cohesive-energy-relation-cubic-crystal"
      "instance-id" 1
      "short-name" {
        "source-value" [ "_LATTICETYPE_" ]
      }
      "species" {
        "source-value" [
          _SPECIES_
        ]
      }
      "a" {
        "source-value" [_LATCONSTARRAY_]
        "source-unit" "angstrom"
      }
      "basis-atom-coordinates" {
        "source-value" [
          _BASISATOMCOORDS_
        ]
      }
      "cohesive-potential-energy" {
        "source-value" [_ECOHARRAY_]
        "source-unit" "eV"
      }
    }

.. _example2_TD_lammpstemplate:

lammps.in.template
^^^^^^^^^^^^^^^^^^
This file is processed by :ref:`example2_TD_exec` using the \`sed` command line utility and the information entered on stdin through :ref:`example2_TE_stdin`.  The processed file is then written to the final LAMMPS input script which is run (``lammps.in`` in the Test Result directory).  Note that when using a KIM Model within LAMMPS, the appropriate LAMMPS 'pair_style' to use is `pair_style kim <http://lammps.sandia.gov/doc/pair_kim.html>`_.

::

    # Define looping variables
    variable loopcount loop sed_numberofspacings_string
    variable latticeconst index sed_latticeconst_string

    # Define unit set and class of atomic model
    units metal
    atom_style atomic

    # Periodic boundary conditions along all three dimensions
    boundary p p p

    # Create a lattice with type and spacing specified by the user (referred to as "a_0" in
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

.. _example2_TD_exec:

runner
^^^^^^

.. code-block:: bash

    #!/usr/bin/env bash

    # Author: Daniel S. Karls (karl0100 |AT| umn DOT edu), University of Minnesota
    # Date: 8/04/2014

    # This example Test Driver illustrates the use of LAMMPS in the OpenKIM Pipeline to compute a cohesive energy versus lattice constant curve
    # for a given cubic lattice (fcc, bcc, sc, diamond) of a single given species.  The curve is computed for lattice constants ranging from
    # a_min_frac*a_0 to a_max_frac*a_0, where a_0, a_min_frac, and a_max_frac are specified via stdin.
    # The parameter a_0 is typically approximately equal to the equilibrium lattice constant for the Model/species/lattice type being paired.
    # A logarithmic scale is used such that most lattice spacings are about a_0. The precise scaling of and number of sample points going
    # from a_min to a_0 and from a_0 to a_max is specified by two separate parameters passed from stdin.
    # Please see README.txt for more details.

    # Define function which prints to stderr
    echoerr() { echo "$@" 1>&2; }

    # Read the KIM Model name from stdin (this is passed through pipeline.stdin.tpl using @< MODELNAME >@, which the pipeline
    # will automatically fill in once a compatible Model is found).
    # Also pass the species, atomic mass (in g/mol), type of cubic lattice (bcc, fcc, sc, or diamond), a_0, a_min_frac, a_max_frac,
    # number of sample spacings between a_min (= a_min_frac*a_0) and a_0, number of sample spacings between a_0 and a_max
    # (= a_max_frac*a_0), and the two parameters governing the distribution of sample spacings around a_0 compared to a_min/a_max
    # respectively.  Please see README.txt for more details on these parameters and how they are used.
    echo "Please enter a valid KIM Model extended-ID:"
    read modelname
    echo "Please enter the species symbol (e.g. Si, Au, Al, etc.):"
    read element
    echo "Please enter the atomic mass of the species (g/mol):"
    read mass
    echo "Please enter the lattice type (bcc, fcc, sc, or diamond):"
    read latticetypeinput
    echo "Please specify a lattice constant (referred to as a_0 below) in Angstroms about which the energy will be computed (This will usually be the equilibrium lattice constant.\
      Most of the volumes sampled will be about this lattice constant.):"
    read a_0
    echo "Please specify the smallest lattice spacing (referred to as a_min below) at which to compute the energy, expressed as a fraction of a_0 (for example, if you wish for\
     a_min to be equal to 0.8*a_0, please specify 0.8 for this value):"
    read a_min_frac
    echo "Please specify the largest lattice spacing (referred to as a_max below) at which to compute the energy, expressed as a multiple of a_0 (for example, if you wish for\
     a_max to be equal to 1.5*a_0, please specify 1.5 for this value):"
    read a_max_frac
    echo "Please enter the number of sample lattice spacings to compute which are >= a_min and < a_0 (one of these sample lattice spacings will be equal to a_min):"
    read N_lower
    echo "Please enter the number of sample lattice spacings to compute which are > a_0 and <= a_max (one of these sample lattice spacings will be equal to a_max):"
    read N_upper
    echo "Please enter a value of the lower sample spacing parameter (see README.txt for more details):"
    read samplespacing_lower
    echo "Please enter a value of the upper sample spacing parameter (see README.txt for more details):"
    read samplespacing_upper

    # Check that element string read in contains no spaces
    if [[ "$element" =~ \  ]] ; then
        echo "Error: a space was detected in the element inputted. Please note that this Test supports only a single species. Exiting..."
        echoerr "Error: a space was detected in the element inputted. Please note that this Test supports only a single species. Exiting..."
        exit 1
    fi

    # Check that a_0 is numerical and strictly positive
    if ! [[ "$a_0" =~ ^[0-9e\.-]+ ]] ; then
        if [[ "${a_0}" == "[]" ]] ; then
            echo "Error: a_0 read in is empty. If using a query, check that it returns a non-empty value. Exiting..."
            echoerr "Error: a_0 read in is empty. If using a query, check that it returns a non-empty value. Exiting..."
            exit 1
        else
            echo "Error: a_0 read in is not numerical. Check pipeline.stdin for errors. Exiting..."
            echoerr "Error: a_0 read in is not numerical. Check pipeline.stdin for errors. Exiting..."
            exit 1
        fi
    fi

    a_0check=`echo $a_0 | awk '{if($1 <= 0.0) print "Not positive"}'`
    if [ "$a_0check" == "Not positive" ]; then
        echo "Error: a_0 read in must be a positive number.  Exiting..."
        echoerr "Error: a_0 read in must be a positive number.  Exiting..."
        exit 1
    fi

    # Check that a_min_frac entered is positive and strictly less than 1
    a_min_fraccheck=`echo $a_min_frac | awk '{if($1 > 0.0 && $1 < 1.0) print "a_min_frac OK"}'`
    if [ "$a_min_fraccheck" != "a_min_frac OK" ]; then
        echo "Error: a_min_frac must be in the range (0,1)."
        echoerr "Error: a_min_frac must be in the range (0,1)."
        exit 1
    else
        a_min=`echo $a_min_frac $a_0 | awk '{print $1*$2}'`
    fi

    # Check that a_min_frac entered is greater than 1
    a_max_fraccheck=`echo $a_max_frac | awk '{if($1 > 1.0) print "a_max_frac OK"}'`
    if [ "$a_max_fraccheck" != "a_max_frac OK" ]; then
        echo "Error: a_max_frac must be strictly greater than 1."
        echoerr "Error: a_max_frac must be strictly greater than 1."
        exit 1
    else
        a_max=`echo $a_max_frac $a_0 | awk '{print $1*$2}'`
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
    spacingparamcheck=`echo $samplespacing_lower $samplespacing_upper | awk '{if($1 <= 1.0 && $2 <=1.0) print 1; else if($1 <= 1.0 && $2 > 1.0) print 2; else if($1 > 1.0 && $2 <= 1.0) print 3; else print 4}'`
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
        basisatomcoords="[   0    0    0 ]\n      [ 0.5  0.5  0.5 ]"
        specieslist="\"${element}\"\n      \"${element}\""
    elif [ `echo $latticetypeinput | tr [:upper:] [:lower:]` = `echo fcc | tr [:upper:] [:lower:]` ]; then
        latticetype="fcc"
        space_group="Fm-3m"
        wyckoffcode="4a"
        basisatomcoords="[   0    0    0 ]\n      [   0  0.5  0.5 ]\n      [ 0.5    0  0.5 ]\n      [ 0.5  0.5    0 ]"
        specieslist="\"${element}\"\n      \"${element}\"\n      \"${element}\"\n      \"${element}\""
    elif [ `echo $latticetypeinput | tr [:upper:] [:lower:]` = `echo sc | tr [:upper:] [:lower:]` ]; then
        latticetype="sc"
        space_group="Pm-3m"
        wyckoffcode="1a"
        basisatomcoords="[ 0 0 0 ]"
        specieslist="\"${element}\""
    elif [ `echo $latticetypeinput | tr [:upper:] [:lower:]` = `echo diamond | tr [:upper:] [:lower:]` ]; then
        latticetype="diamond"
        space_group="Fd-3m"
        wyckoffcode="8a"
        basisatomcoords="[    0     0     0 ]\n      [    0   0.5   0.5 ]\n      [  0.5   0.5     0 ]\n      [  0.5     0   0.5 ]\n      [ 0.75  0.25  0.75 ]\n      [ 0.25  0.25  0.25 ]\n      [ 0.25  0.75  0.75 ]\n      [ 0.75  0.75  0.25 ]"
        specieslist="\"${element}\"\n      \"${element}\"\n      \"${element}\"\n      \"${element}\"\n      \"${element}\"\n      \"${element}\"\n      \"${element}\"\n      \"${element}\""
    else
        echo "Error: This Test supports only cubic lattices (specified by 'bcc', 'fcc', 'sc', or 'diamond'). Exiting..."
        echoerr "Error: This Test supports only cubic lattices (specified by 'bcc', 'fcc', 'sc', or 'diamond'). Exiting..."
        exit 1
    fi

    # Define the lattice spacings at which the energy will be computed.  See README.txt for more details.
    latticeconst=`echo $a_0 $a_min $a_max $N_lower $N_upper $samplespacing_lower $samplespacing_upper |  awk '{for (i=0;i<=$5-1;++i){printf "%f ",$1+($3-$1)*(1-log(1+i*($7-1)/$5)/log($7))}}{for (i=$4;i>=0;--i){printf "%f ",$2+($1-$2)*log(1+i*($6-1)/$4)/log($6)}}'`
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

    for ((i=1; i<=$numberofspacings;++i)); do
        j=`expr $i - 1`
        latconstarray="$latconstarray ${lattice_const[$j]} "
    done

    for ((i=1; i<=$numberofspacings;++i)); do
        j=`expr $i - 1`
        # Check to see that the cohesive energies parsed from LAMMPS are actually numbers (in case there was a LAMMPS error of some sort)
        if ! [[ "${cohesive_energy[$j]}" =~ ^[0-9e.-]+ ]]; then
            echo "Error: Cohesive energies parsed from LAMMPS output are not numerical.  Check the LAMMPS log for errors.  Exiting..."
            echoerr "Error: Cohesive energies parsed from LAMMPS output are not numerical.  Check the LAMMPS log for errors.  Exiting..."
            exit 1
        fi

        ecoh=`echo ${cohesive_energy[$j]} | awk '{print $1*(-1)}'`
        ecoharray="$ecoharray $ecoh "
    done

    # Replace the placeholders in the EDN results template file (results.edn.tpl) with results
    sed "s/_LATTICETYPE_/${latticetype}/" ""$thisdir"/results.edn.tpl" >  output/results.edn
    sed -i "s/_SPECIES_/${specieslist}/" output/results.edn
    sed -i "s/_LATCONSTARRAY_/${latconstarray}/" output/results.edn
    sed -i "s/_BASISATOMCOORDS_/${basisatomcoords}/" output/results.edn
    sed -i "s/_ECOHARRAY_/${ecoharray}/" output/results.edn

The Test Driver begins by reading the Model name, atomic species, atomic mass, and lattice type from stdin.  The parameters which determine the precise lattice spacings for which the cohesive energy will be computed are then read in (see ``README.txt`` for further explanation of these parameters).  After some error-checking is done to ensure that the user-specified parameters are valid, the array of lattice constants and the number of lattice constants are computed.  Once the LAMMPS input template :ref:`example2_TD_lammpstemplate` is processed with \`sed` and a functioning LAMMPS input script ``lammps.in`` is written to the Test Result directory (``output/``), LAMMPS is invoked.

The LAMMPS input script for this example utilizes the `next <http://lammps.sandia.gov/doc/next.html>`_ and `jump <http://lammps.sandia.gov/doc/jump.html>`_ commands within LAMMPS in order to loop over the set of lattice constants, and the result for each lattice constant is successively concatenated onto ``lammps.log``.  Using \`grep` to extract the cohesive energies from ``lammps.log``, the relevant placeholder strings in :ref:`example2_TD_resultstemplate` are replaced with the corresponding values to render a file named ``results.edn`` in the Test Result directory.

.. _example2_TD_makefile:

Makefile
^^^^^^^^
As there is no need to compile :ref:`example2_TD_exec`, the Makefile is uninteresting.

::

    all:
                @echo "Nothing to make"

    clean:
                @echo "Nothing to clean"

.. _example2_TE_ref:

Test
----
We consider next a particular Test which uses the Test Driver above.  This Test computes a cohesive energy versus lattice constant curve for fcc argon.

List of files
^^^^^^^^^^^^^

    * :ref:`example2_TE_kimspec` - a file which describes the metadata associated with the Test
    * :ref:`example2_TE_kimfile` - a KIM descriptor file which outlines the capabilities of the Test
    * :ref:`example2_TE_stdin` - a `Jinja`_ template file processed by the pipeline and used to provide input to the Test on stdin
    * :ref:`example2_TE_deps` - a file indicating which OpenKIM Test Results this Test depends on
    * :ref:`example2_TE_exec` - the main executable, a python script
    * :ref:`example2_TE_makefile` - a Makefile
    * ``README.txt`` - a file which contains a basic explanation of the Test
    * ``LICENSE.CDDL`` - a copy of the `CDDL license <http://opensource.org/licenses/CDDL-1.0>`_

.. _example2_TE_kimspec:

kimspec.edn
^^^^^^^^^^^
This EDN-formatted file (see `About the EDN data format`_) contains metadata associated with the Test.  More information on these files can be found `here <https://kim-items.openkim.org/kimspec-format>`_. This file must always be named ``kimspec.edn``.

.. code-block:: clojure

    {
      "extended-id" "LammpsExample2_fcc_Ar__TE_778998786610_001"
      "test-driver" "LammpsExample2__TD_887699523131_001"
      "species" "Ar"
      "description" "This example Test illustrates the use of LAMMPS in the openkim-pipeline to compute an energy vs.
    lattice constant curve for fcc Argon.  The curve is computed for lattice constants
    ranging from  Angstroms to  Angstroms, with most lattice spacings sampled about
     Angstroms."
      "kim-api-version" "1.6"
      "domain" "openkim.org"
      "title" "LammpsExample2_fcc_Ar: energy-volume curve of fcc Argon"
      "pipeline-api-version" "1.0"
    }

.. _example2_TE_kimfile:

descriptor.kim
^^^^^^^^^^^^^^
As always, the .kim descriptor file outlines the essential details of a Test, including the units it uses, the atomic species it supports, the neighborlist methods it contains, what information it passes to a Model, and what information it expects to receive from a Model.

::

    TEST_NAME        := LammpsExample2_fcc_Ar__TE_778998786610_001
    KIM_API_Version  := 1.6.0
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
    NEIGH_RVEC_H      flag
    NEIGH_RVEC_F      flag

    MODEL_INPUT:
    numberOfParticles            integer  none    []
    numberOfSpecies              integer  none    []
    particleSpecies              integer  none    [numberOfParticles]
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

.. _example2_TE_stdin:

pipeline.stdin.tpl
^^^^^^^^^^^^^^^^^^
This `Jinja`_ template is used to input information to :ref:`example2_TD_exec` on stdin.  As in Example 1, since our Test is derived from a Test Driver the first line of this file must include a reference of the form ``@< path(" ... ") >@`` to the path of the Test Driver.


.. code-block:: jinja

    @< path("LammpsExample2__TD_887699523131_001") >@
    @< MODELNAME >@
    Ar
    39.948
    fcc
    @< query({"flat": "on", "database": "data", "fields": {"_id": 0, "meta.runner._id": 1, "a.source-value": 1}, "limit": 1, "query": {"meta.runner._id": {"$regex":
    "TE_206669103745"
    }, "meta.subject._id": MODELNAME},"project":["a.source-value"]}) >@
    0.85
    1.5
    13
    24
    5
    50

An interesting distinction we notice from the last example is the presence of a ``@< query() @>`` operation.  As previously mentioned, directives of the form ``@< >@`` in this file are interpreted as python code which evaluates to a variable.  In this case, we see that the pipeline has a function named ``query()`` which takes as input a `JSON <json.org>`_ dictionary and requests data from the OpenKIM Repository.  Let's take a closer look at the JSON dictionary we see in the query of the file above.

.. code-block:: json

    {
        "flat": "on",
        "database": "data",
        "fields": {"_id": 0,"meta.runner._id": 1, "a.source-value": 1},
        "limit": 1,
        "query": {"meta.runner._id": {"$regex":"TE_206669103745"}, "meta.subject._id": MODELNAME},
        "project":["a.source-value"]
    }

The most important key in this dictionary is ``query``, which defines what information we're retrieving from the repository.  In this example, we wish to request all pieces of data in the repository which feature a Test name (known as "meta.runner._id" in the repository) that includes the string "TE_206669103745" and a Model name (known as "meta.subject._id") exactly matching the name of whichever Model is currently executing with our Test.  A quick search with ``kimitems``:

.. code-block:: bash

    kimitems search "TE_206669103745"

reveals there are currently two items in the OpenKIM Repository which contain the above string: ``LatticeConstantCubicEnergy_fcc_Ar__TE_206669103745_000`` and ``LatticeConstantCubicEnergy_fcc_Ar__TE_206669103745_001``, which are actually two different versions of the same Test.  However, by default, a query on a KIM Item with its three-digit version omitted will only use the latest version (version "001" in this case).  ``LatticeConstantCubicEnergy_fcc_Ar__TE_206669103745_001`` computes the lattice constant and cohesive energy of an fcc argon crystal and reports these quantities in the form of two properties: `cohesive-potential-energy-cubic-crystal`_, like the Test of Example 1, and `structure-cubic-crystal-npt`_.  Although the lattice constant is reported in both of these properties, this Test reports both of them in order to improve its queriability.

The ``fields`` key indicates what information we'd like the query to return, which in this case is the Extended KIM ID of the Test and the value of ``a.source-value``, which represents the lattice constant in both of the two aforementioned properties.  In order to prevent getting back two copies of the same value for lattice constant, the ``limit`` key has been used to constrain the number of results we receive back from the query to only one.

The ``database`` key indicates which section of the repository we're querying for information.  The value of "data" means that we're looking at the part of the repository that houses actual Test Results.  The ``flat`` key indicates that we want to decrease the nesting of the query results as much as possible, while the ``limit`` key can be used to constrain how many results we get back (with a default value of "0" indicating no limit).

Finally, we use ``project`` to transform the single-element JSON array we get back into a scalar value.

.. note::
    For more information on querying the OpenKIM Repository, as well as a graphical querying interface, please visit `<https://query.openkim.org>`_ or click on "Query" in the navigation bar at the top of this page.

.. _example2_TE_deps:

dependencies.edn
^^^^^^^^^^^^^^^^

The fact that our Test performs a query inside of ``pipeline.stdin.tpl`` means that our Test now has a "dependency", i.e. there is data that our Test needs in order for it to successfully run.  This dependency, or multiple dependencies in general, is conveyed to the pipeline in the form of the ``dependencies.edn`` file, which is used to indicate to the pipeline which Test Results or Reference Data are required by a Test at run time.

.. code-block:: clojure

    [ "TE_206669103745" ]

In this file, each KIM Item (Test Results or Reference Data) our Test depends on is represented as an EDN array which can include either one or two strings; single-string arrays can also be represented as scalars, e.g. the [] brackets in the file above could have been left out.  By default, if only a Test name is given as above, then it is assumed by the pipeline that the Test Result(s) we're referring to pertain(s) to that (those) Test(s) when run against the Model that our Test is currently running against.  Moreover, if the three-digit version extension of a KIM Item is omitted, then our Test is assumed to depend on potentially all currently existing versions of that item.

This file can be omitted if your Test has no dependencies, but if it is included it must be named ``dependencies.edn``.

.. Add links to pipeline docs for dependencies.edn.

.. _example2_TE_exec:

runner
^^^^^^

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

.. _example2_TE_makefile:

Makefile
^^^^^^^^
As there is no need to compile :ref:`example2_TE_exec`, the Makefile is uninteresting.

::

    all:
                @echo "Nothing to make"

    clean:
                @echo "Nothing to clean"

.. _example2_calc_ref:

Example Calculation
-------------------
We can run this Test against the same Model as in the first example, `Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_001`_.  We once again use ``pipeline_runpair``

.. code-block:: bash

    pipeline_runpair LammpsExample2_fcc_Ar__TE_778998786610_001 Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_001

which, as in Example 1, produces output similar to the following:

::

    2014-08-10 20:08:57,855 - INFO - pipeline.development - Running combination <<Test(LammpsExample2_fcc_Ar__TE_778998786610_001)>,
    <Model(Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_001)>
    2014-08-10 20:09:07,844 - INFO - pipeline.compute - running <Test(LammpsExample2_fcc_Ar__TE_778998786610_001)> with
    <Model(Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_001)>
    2014-08-10 20:09:08,089 - INFO - pipeline.compute - launching run...
    2014-08-10 20:09:08,611 - INFO - pipeline.compute - Run completed in 0.5218360424041748 seconds
    2014-08-10 20:09:09,194 - INFO - pipeline.compute - Copying the contents of /home/openkim/openkim-repository/te/LammpsExample2_fcc_Ar
    _running2f628a54-20ca-11e4-b6ec-41cabcba9ab3__TE_778998786610_001/output to /home/openkim/openkim-repository/tr/2f628a54-20ca-11e4-b6
    ec-41cabcba9ab3

If we go to to the directory where our Test Result was stored, we can look at the final ``results.edn`` that the Test generated:

.. code-block:: clojure

    {
        "short-name" {
            "source-value" [
                "fcc"
            ]
        }
        "a" {
            "si-unit" "m"
            "source-unit" "angstrom"
            "si-value" [
                7.87276e-10
                7.12654e-10
                6.782034e-10
                6.555538e-10
                6.386516e-10
                6.251625e-10
                6.139371e-10
                6.043236e-10
                5.959167e-10
                5.88447e-10
                5.817264e-10
                5.756181e-10
                5.7002e-10
                5.648533e-10
                5.600562e-10
                5.555794e-10
                5.513827e-10
                5.474332e-10
                5.437034e-10
                5.401701e-10
                5.368136e-10
                5.33617e-10
                5.305659e-10
                5.276476e-10
                5.248509e-10
                5.217441e-10
                5.184264e-10
                5.148673e-10
                5.110287e-10
                5.068631e-10
                5.023095e-10
                4.97288e-10
                4.916915e-10
                4.853709e-10
                4.781107e-10
                4.69582e-10
                4.592455e-10
                4.46123e-10
            ]
            "source-value" [
                7.87276
                7.12654
                6.782034
                6.555538
                6.386516
                6.251625
                6.139371
                6.043236
                5.959167
                5.88447
                5.817264
                5.756181
                5.7002
                5.648533
                5.600562
                5.555794
                5.513827
                5.474332
                5.437034
                5.401701
                5.368136
                5.33617
                5.305659
                5.276476
                5.248509
                5.217441
                5.184264
                5.148673
                5.110287
                5.068631
                5.023095
                4.97288
                4.916915
                4.853709
                4.781107
                4.69582
                4.592455
                4.46123
            ]
        }
        "property-id" "tag:staff@noreply.openkim.org,2014-04-15:property/cohesive-energy-relation-cubic-crystal"
        "cohesive-potential-energy" {
            "si-unit" "kg m^2 / s^2"
            "source-unit" "eV"
            "si-value" [
                2.2495519e-21
                3.989099e-21
                5.2419048e-21
                6.2728573e-21
                7.1628824e-21
                7.9531078e-21
                8.6618146e-21
                9.301868e-21
                9.884099e-21
                1.0413458e-20
                1.0894784e-20
                1.1331842e-20
                1.1728829e-20
                1.2086931e-20
                1.2408088e-20
                1.2693948e-20
                1.2945874e-20
                1.3165869e-20
                1.3354109e-20
                1.3511394e-20
                1.3638479e-20
                1.3736004e-20
                1.3804497e-20
                1.3845785e-20
                1.3859708e-20
                1.3841122e-20
                1.3776587e-20
                1.3648909e-20
                1.3433497e-20
                1.309422e-20
                1.257654e-20
                1.1795495e-20
                1.0613714e-20
                8.7978714e-21
                5.9181995e-21
                1.131175e-21
                -7.4299972e-21
                -2.4632982e-20
            ]
            "source-value" [
                0.0140406
                0.024898
                0.0327174
                0.0391521
                0.0447072
                0.0496394
                0.0540628
                0.0580577
                0.0616917
                0.0649957
                0.0679999
                0.0707278
                0.0732056
                0.0754407
                0.0774452
                0.0792294
                0.0808018
                0.0821749
                0.0833498
                0.0843315
                0.0851247
                0.0857334
                0.0861609
                0.0864186
                0.0865055
                0.0863895
                0.0859867
                0.0851898
                0.0838453
                0.0817277
                0.0784966
                0.0736217
                0.0662456
                0.054912
                0.0369385
                0.00706024
                -0.0463744
                -0.153747
            ]
        }
        "basis-atom-coordinates" {
            "source-value" [
                [
                    0
                    0
                    0
                ]
                [
                    0
                    0.5
                    0.5
                ]
                [
                    0.5
                    0
                    0.5
                ]
                [
                    0.5
                    0.5
                    0
                ]
            ]
        }
        "species" {
            "source-value" [
                "Ar"
                "Ar"
                "Ar"
                "Ar"
            ]
        }
        "instance-id" 1
    }

.. Add a link to visualizer for the CohesiveEnergy_fcc_Ar test

.. The ``testgenie`` utility included on the OpenKIM Virtual Machine was used to generate the Tests LammpsExample2_diamond_Si__TE_837477125670_001 and LammpsExample2_fcc_Ar__TE_778998786610_001.  This utility operates using a file named ``test_generator.json`` in the Test Driver directory and the template files found in ``test_template/``.  To generate these two Tests, enter the LammpsExample2__TD_887699523131_000 directory and issue, for example, the command ``testgenie --destination ~/openkim-repository/te/ LammpsExample2__TD_887699523131_000``.  For more information on ``testgenie``, enter the command ``testgenie --h``.

.. _About the EDN data format: https://openkim.org/about-edn/
.. _KIM Properties Framework: https://openkim.org/properties-framework/
.. _Jinja: http://jinja.pocoo.org/
.. _units metal: http://lammps.sandia.gov/doc/units.html
.. _click here: https://openkim.org/cite/MO_126566794224_001
.. _Pair_Lennard_Jones_Shifted_Bernardes_MedCutoff_Ar__MO_126566794224_001: https://openkim.org/cite/MO_126566794224_001
.. _cohesive-potential-energy-cubic-crystal: https://kim-items.openkim.org/properties/show/2014-04-15/staff@noreply.openkim.org/cohesive-potential-energy-cubic-crystal
.. _cohesive-energy-relation-cubic-crystal: https://kim-items.openkim.org/properties/show/2014-04-15/staff@noreply.openkim.org/cohesive-energy-relation-cubic-crystal
.. _structure-cubic-crystal-npt: https://kim-items.openkim.org/properties/show/2014-04-15/staff@noreply.openkim.org/structure-cubic-crystal-npt
