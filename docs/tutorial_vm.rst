Using the Virtual Machine
=========================

In order to facilitate the process of Test and Model development, a virtual machine (VM) has been created for KIM users which features an operating environment which exactly mirrors that used by the `OpenKIM Pipeline`_ to run Test-Model pairs in the OpenKIM Repository.  This ensures that any Tests and/or Models which run as intended on the VM will also execute properly after they have been formally submitted to the OpenKIM Repository.

To begin using the VM, please visit the OpenKIM Pipeline `downloads page`_ and choose one of the three methods listed on the left to get started.  Detailed instructions for downloading and installing the VM can be found within each of the tabs on this page.  Note that unless you plan to use the LiveCD ISO, you will have to install `VirtualBox`_.  Moreover, it is recommended that you download and use `Vagrant`_ to automatically configure the VM.

Directory Structure
-------------------

After booting the VM and logging in, you will find yourself in a bash shell with the following directory structure in the home directory:

::

    ~
    ├── bin - contains binaries necessary to build and run Tests (lammps, make, etc)
    ├── builds - contains several auxiliary packages used by the pipeline (openkim-kimcalculator-ase, openkim-python, etc)
    ├── openkim-api - contains the source code of the KIM API
    ├── openkim-pipeline - contains the pipeline code
    │   ├── logs - where the pipeline logs live
    │   └── tools - various command line tools to help with the development process
    ├── openkim-pipeline-setup - contains the code that created the VM you are currently running
    ├── openkim-repository - contains an empty copy of the OpenKIM Repository
    └── openkim-website - contains code to run the remote viewing panel for the VM

In addition to the standard KIM directories, it is important to note the existence of the ``/vagrant/`` directory.  This directory is shared between the VM and the primary OS you're running, and can be conveniently used to transfer files between the two.  Anything that you copy into ``/vagrant/`` on the VM will show up in the folder you installed the VM into on your primary OS.  Likewise, anything you place in the folder where you installed the VM will show up in ``/vagrant/`` on the VM.

Tools and Scripts
-----------------

Of particular interest are the tools listed in ``~/openkim-pipeline/tools``, which should all be on ``PATH`` so they can be invoked from any directory.

+ ``kimitems`` - a simple package manager with an interface to the official openkim.org repository
+ ``kimunits`` - used by the pipeline to perform unit conversions
+ ``pipeline_runpair`` - run a specific Test-Model pair
+ ``pipeline_runmatches`` - run all of the compatible Models (Tests) for a specified Test (Model)
+ ``pipeline_verify`` - run all verification results for a particular object (Test or Model)
+ ``pipeline_verifyresult`` - run property verification checks on a test result
+ ``testgenie`` - creates a set of Tests from a template - this is typically used when creating many Tests that use a Test Driver

Additionally, it should be known that bash completions have been added so that you should be able to tab-complete on any of the KIM items you have in your local repository (i.e. all items contained in ``~/openkim-repository/`` on your VM) on the command line.

Finally, the executables in ``~/bin/`` are also on ``PATH``.  This includes ``makekim``, which will attempt to build all of the KIM items in your entire local repository.


Local Repository
----------------

By default, the VM makes some assumptions about the directory structure of ``~/openkim-repository``. The default layout is

::

    ~/openkim-repository/
    ├── er - Pipeline errors
    ├── md - Model Drivers
    ├── mo - Models
    ├── rd - Reference Data
    ├── td - Test Drivers
    ├── te - Tests
    └── tr - Test Results

In each of these directories, each KIM Item will have an individual directory named for its `Extended KIM ID`_.

.. #### In order to get some example Tests and Models for your repository, please see instructions at `this page (FIXME)`_.

Getting Started Tutorial
------------------------

Here, we'll run through the basics of downloading Tests and Models and running them on the VM.


Downloading Content
~~~~~~~~~~~~~~~~~~~

First, let’s get a Model. This can be either done graphically by going to the `KIM Items`_ pages on the OpenKIM website or through command line via the ``kimitems`` utility.  In this example, we're going to use the ``EAM_Dynamo_Ackland_Bacon_Fe__MO_142799717516_000`` Model.  If you'd like to download the the Model using your web browser, navigate to `this Model's KIM Items page`_.  At the bottom of this page, you will see a "Download" section where links to an archive of this Model are provided.  Simply click on the link corresponding to your desired archive format to queue the download.  Having downloaded an archive of the Model, the next step is to transfer this archive onto the VM.  In order to do this, copy the archive file into the directory where you installed the VM on your primary OS.  After doing this, you'll notice that if you look in the ``/vagrant/`` directory on your VM, you'll see the archive.  From here, decompress the archive and copy the resulting folder into ``~/openkim-repository/mo/``.

.. code-block:: bash

    cd /vagrant
    tar xvJ EAM_Dynamo_Ackland_Bacon_Fe__MO_142799717516_000.txz
    cp -r EAM_Dynamo_Ackland_Bacon_Fe__MO_142799717516_000 ~/openkim-repository/mo/

.. note::

    The KIM Items page of KIM content can always be referenced by a permanent URL of the form openkim.org/cite/<KIM short ID>.  For example, the link above to the KIM Items page of the Model above is openkim.org/cite/MO_142799717516_000.

Alternatively, you can download the archive directly from within the VM by using the ``kimitems`` utility.  From any location, we can issue

.. code-block:: bash

    kimitems install EAM_Dynamo_Ackland_Bacon_Fe__MO_142799717516_000

to automatically download a ``.tar.gz`` archive of a KIM Item into the current directory, decompress it, and copy it to the appropriate directory under ``~/openkim-repository/``.  It will then delete the ``.tar.gz`` that was downloaded.

If you downloaded the Model using your browser, you may have noticed that under the "Download" section of its KIM Items page, there was also a section labeled "Download Dependency".  This is present to indicate that this Model is derived from a Model Driver (``EAM_Dynamo__MD_120291908751_000``), and thus the Model Driver must also be downloaded.  Repeat the above steps to download ``EAM_Dynamo__MD_120291908751_000``, only this time place the archive in ``~/openkim-repository/md/`` instead of ``~/openkim-repository/mo/``. If you use ``kimitems``, it will place the Model Driver in the correct directory automatically.

.. code-block:: bash

    kimitems install EAM_Dynamo__MD_120291908751_000

Having obtained a Model and its corresponding Model Driver, we'll also want to download a Test to run against this Model.  In this case, a Test which is compatible with our Model is ``LatticeConstantCubicEnergy_fcc_Fe__TE_342002765394_000``, which computes the lattice constant and cohesive energy of fcc iron.  Examination of `this Test's KIM Items page`_ indicates that it also requires a Test Driver (``LatticeConstantCubicEnergy__TD_475411767977_000``) in order to run.  Let's download the Test and its Test Driver directly from the VM:

.. code-block:: bash

    kimitems install LatticeConstantCubicEnergy_fcc_Fe__TE_342002765394_000
    kimitems install LatticeConstantCubicEnergy__TD_475411767977_000


Building Content
~~~~~~~~~~~~~~~~

Now that we've downloaded a Test and Model to run, we need to compile them.  This can be accomplished by issuing the ``makekim`` command from any directory, which will attempt to compile all of the Models, Model Drivers, Tests, and Test Drivers under ``~/openkim-repository/``.  If you're only looking to compile or recompile a small subset of your local repository, you can do so by manually navigating to the directory of each KIM Item and issuing the ``make`` command (preceeded by ``make clean`` in the case of recompilation).  In the case of our example, this would amount to the following:

.. code-block:: bash

    cd ~/openkim-repository/md/EAM_Dynamo__MD_120291908751_000 && make
    cd ~/openkim-repository/mo/EAM_Dynamo_Ackland_Bacon_Fe__MO_142799717516_000 && make
    cd ~/openkim-repository/td/LatticeConstantCubicEnergy__TD_475411767977_000 && make
    cd ~/openkim-repository/te/LatticeConstantCubicEnergy_fcc_Fe__TE_342002765394_000 && make

.. warning::

    When manually compiling/recompiling Models which a Model Driver or Tests which use a Test Driver, you'll want to make sure that you first compile or recompile the relevant Model Driver or Test Driver **before** you compile/recompile the individual Models or Tests, respectively.

If for some reason you encounter compilation problems that you don't believe are specifically related to a KIM Item, try rebuilding the KIM API itself on your VM by entering

.. code-block:: bash

    cd ~/openkim-api/KIM_API && make clean
    cd .. && make openkim-api

Running the Test-Model pair
~~~~~~~~~~~~~~~~~~~~~~~~~~~

With the Model and Test compiled, we're ready to run them.  We can do this at the command line by entering

.. code-block:: bash

     pipeline_runpair LatticeConstantCubicEnergy_fcc_Fe__TE_342002765394_000 EAM_Dynamo_Ackland_Bacon_Fe__MO_142799717516_000

.. note::

    As you're typing the Test and Model names, try using the tab key to autocomplete their names.

.. note::

    The ``pipeline_runmatches`` utility can be used to run a Test (Model) against all compatible Models (Tests) in your local repository.

You should see output similar to the following:

.. code-block:: bash

    2014-08-05 15:49:46,744 - INFO - pipeline.development - Running combination <<Test(LatticeConstantCubicEnergy_fcc_Fe__TE_342002765394_000)>, <Model(EAM_Dynamo_Ackland_Bacon_Fe__MO_142799717516_000)>
    2014-08-05 15:49:46,989 - INFO - pipeline.compute - running <Test(LatticeConstantCubicEnergy_fcc_Fe__TE_342002765394_000)> with <Model(EAM_Dynamo_Ackland_Bacon_Fe__MO_142799717516_000)>
    2014-08-05 15:49:46,996 - INFO - pipeline.compute - launching run...
    2014-08-05 15:49:47,317 - INFO - pipeline.compute - Run completed in 0.3207240104675293 seconds
    2014-08-05 15:49:47,499 - INFO - pipeline.compute - Copying the contents of /home/openkim/openkim-repository/te/LatticeConstantCubicEnergy_fcc_Fe_running2053bdf0-1cb8-11e4-8a62-237f1482a623__TE_342002765394_000/output to /home/openkim/openkim-repository/tr/2053bdf0-1cb8-11e4-8a62-237f1482a623

The last line indicates that the results of the run have been copied to ``~/openkim-repository/tr/`` into a unique directory named with a pseudo-random UUID code. Go to this directory and inspect the results.

.. note::

    If an error occurs while attempting to run a Test-Model pair, a similar dialog will be shown but with additional information including the pipeline's error messages along with excerpts of the stdout and stderr generated by the run.  In this case, the Test Result will be placed under its own UUID-titled directory under ``~/openkim-repository/er/``, and within this directory you can view the actual files that were output from the run attempt.

Examining Output
~~~~~~~~~~~~~~~~

In the directory of your Test Result under ``~/openkim-repository/tr/``,  you should find the following files:

::

    .
    ├── kim.log - the kim log for the run
    ├── kimspec.edn - some metadata for the Test Result
    ├── pipelinespec.edn - some metadata about the run itself, generated by the pipeline
    ├── pipeline.stderr - the stderr output from the run
    ├── pipeline.stdin - the stdin that was input to the Test executable
    ├── pipeline.stdout - the stdout output from the run
    └── results.edn - the results file that every Test must generate

In general, the standard I/O streams from the run saved in ``pipeline.stdin``, ``pipeline.stdout``, and ``pipeline.stderr`` can be useful diagnostic tools for Test or Model development since they will catch any debugging or diagnostic messages that are output.  However, the primary outcome of running the Test-Model pair is ``results.edn``.  In the OpenKIM framework, a Test Result is encapsulated in a structured `edn`_ document (see also `about edn in KIM`_) that every Test must generate and which must always bear this standard name.  This file contains what is referred to in KIM as a "Property Instance", which is a specific occurrence (typically including numerical values) of a "Property Definition" (see the `KIM Properties Framework`_ for more details).  The Property Definitions which are currently in the OpenKIM Repository can be found by going to the `KIM Items`_ page and clicking on "Properties" at the top.

Examining the Test
~~~~~~~~~~~~~~~~~~

Now that we've seen how to run a Test-Model pair, let’s take a closer look at the layout of the Test itself. We start by going to the appropriate directory in our local repository:

.. code-block:: bash

     cd ~/openkim-repository/te/LatticeConstantCubicEnergy_fcc_Fe__TE_342002765394_000/

The Test has the following layout:

::

    LatticeConstantCubicEnergy_fcc_Fe__TE_342002765394_000/
    ├── descriptor.kim
    ├── kimspec.edn
    ├── LICENSE.CDDL
    ├── Makefile
    ├── pipeline.stdin.tpl
    ├── results.edn.tpl
    └── runner

+ ``runner`` (REQUIRED) is the Test executable. The executable of all Tests and Test
  Drivers must always share this name.  In this example, this file
  simply reads the Test Driver and input parameters from stdin and executes
  the Test Driver with those inputs.
+ ``descriptor.kim`` (REQUIRED) is the KIM descriptor file of the Test, as described
  in `~/openkim-api/DOCS/standard.kim`_.  This file tells the KIM API about
  the operational parameters of our Test, such as which atomic species and
  neighbor list methods the it supports.  This information is used to determine
  whether a given Model is compatible with this Test (i.e. can be run with it). The
  name of this file for a Test must always be ``descriptor.kim``.
+ ``pipeline.stdin.tpl`` (REQUIRED) this is the file that the pipeline will use
  as a template to form what will actually be passed into the Test’s
  executable at runtime.
+ ``kimspec.edn`` (REQUIRED) this file includes metadata about the Test such as its Extended KIM ID and that of its Test Driver, which
  atomic species it supports, and which version of the pipeline it was designed for.
+ ``results.edn.tpl`` (OPTIONAL) this specific Test happens to use its own template file to generate
  the ``results.edn`` Property Instance file we saw in the Test Result folder.  However, the Test
  may generate ``results.edn`` in any way it likes, including writing it line-by-line.  It should
  be emphasized, however, that every Test must eventually output a valid ``edn`` Property Instance named
  ``results.edn``.
+ ``LICENSE.CDDL`` (OPTIONAL) in this case, the Test conforms to the Creative Development and
  Distribution License (CDDL), so it includes the standard CDDL license file.
+ ``Makefile`` (OPTIONAL) this file is included here, but simply includes messages indicating that
  the Test doesn't need to be compiled, since it is a python executable. It could
  just as well have been ommitted.

In this particular case, the Test itself is rather bare and it's the Test Driver that does most of the heavy lifting.

Examining the Test Driver
~~~~~~~~~~~~~~~~~~~~~~~~~

To take a closer look at the Test Driver, let's visit its folder in our local repository:

.. code-block:: bash

     cd ~/openkim-repository/td/LatticeConstantCubicEnergy__TD_475411767977_000

There, we find the following:

::

    LatticeConstantCubicEnergy__TD_475411767977_000/
    ├── kimspec.edn
    ├── LICENSE.CDDL
    ├── Makefile
    ├── runner
    ├── test_generator.json
    └── test_template
        ├── descriptor.kim.genie
        ├── kimspec.edn.genie
        ├── Makefile
        ├── pipeline.stdin.tpl.genie
        ├── results.edn.tpl
        └── runner

Inside are the following:

+ ``runner`` (REQUIRED) As with the Test, this is the main executable of the
  Test Driver and must be named ``runner``.  This Test Driver consists of a python
  script which makes use of the OpenKIM `ASE`_ interface to compute the lattice constant
  for a given Model and cubic material by minimizing its energy.
+ ``kimspec.edn`` (REQUIRED) metadata for the Test Driver, as for the Test.
+ ``LICENSE.CDDL`` (OPTIONAL) in this case, the Test conforms to the Creative Development and
  Distribution License (CDDL), so it includes the standard CDDL license file.
+ ``Makefile`` (OPTIONAL) this file is included here, but simply includes messages indicating that
  the Test doesn't need to be compiled, since it is a python executable. It could
  just as well have been ommitted.
+ ``test_generator.json`` (OPTIONAL) used by ``testgenie`` to create Tests for this Test Driver
  from a template
+ ``test_template`` (OPTIONAL) The contents of this folder serve as a template which ``testgenie``
  uses to create a large number of Tests which use this Test Driver, including the Test above.
  See below for more information on ``testgenie``.

.. note::

    You can find the OpenKIM Calculator written to interface with ASE in ``~/builds/openkim-kimcalculator-ase/``.

Templating Test Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~

The Test we've seen above computes the lattice constant and cohesive energy of fcc iron.  However, one could readily create another Test which computes the same quantities for bcc nickel without making any substantive changes to the algorithm used.  It is this idea that has led to the creation of ``testgenie``, a utility created for creating many Tests from a single template which all use the same Test Driver.  By creating many Tests which all reference a single Test Driver executable, unnecessary duplication of code is avoided and the debugging process is simplified.

``testgenie`` should be on the ``PATH`` of the VM.  To view its associated help, try typing

.. code-block:: bash

    testgenie -h

To use it, you need to provide a folder that acts as a template for the
generation of a Test, as well as a list of ``json`` dictionaries
describing the actual variable substitutions that should be made. In
this case, this corresponds to the ``test_template`` directory and
``test_generator.json`` file, respectively.

To demonstrate how to invoke ``testgenie``, remove the current Test we
downloaded earlier (but do not delete the Test Driver):

.. code-block:: bash

    rm -rf ~/openkim-repository/te/LatticeConstantCubicEnergy_fcc_Fe__TE_342002765394_000/

Next, issue the command


.. code-block:: bash

    testgenie LatticeConstantCubicEnergy__TD_475411767977_000

After ``testgenie`` finishes running, you'll notice that in ``~/openkim-repository/te/`` that
there are now many new Tests in addition to the original fcc iron Test from before.  In fact,
there is now a ``LatticeConstantCubicEnergy_*`` Test for each every combination of basic
cubic crystal structure and nearly every element!  In total, 416 new Tests have been
generated from a single set of template files in ``~/openkim-repository/td/LatticeConstantCubicEnergy__TD_475411767977/test_template/``,
each of which will simply "point to" the Test Driver executable.

Going Further
-------------

At this point, feel free to start experimenting with different Models
and generating your own Tests or Models. For additional resources to
get you started with KIM, please see the `Getting Started Page`_.
Users who plan to create Tests which make use of LAMMPS or ASE, in particular,
may want to visit the `LAMMPS Example Tests`_ or `ASE Example Tests`_.

..
    #### Add link to "Information for Developers" page and pipeline docs ####
    #### Check Branding for consistency ####
    #### Mention instance validators? ####

.. _edn: https://github.com/edn-format/edn
.. _about edn in KIM: https://openkim.org/about-edn/
.. _Lammps Example Tests: https://pipeline.openkim.org/docs/tutorial_lammps.html
.. _ASE Example Tests: https://pipeline.openkim.org/docs/tutorial_ase.html
.. _the pipeline docs page: https://pipeline.openkim.org/docs/developers.html#pipelineindocs
.. _Jinja2: http://jinja.pocoo.org/docs/
.. _here: https://pipeline.openkim.org/docs/developers.html#pipelineoutdocs
.. _ASE: https://wiki.fysik.dtu.dk/ase/
.. _EAM_Dynamo_Ackland_Bacon_Fe__MO_142799717516_000: https://openkim.org/cite/MO_142799717516_000
.. _Getting Started Page: https://openkim.org/getting-started/
.. _Extended KIM ID: https://openkim.org/about-kim-ids/
.. _OpenKIM Pipeline: https://pipeline.openkim.org/docs/
.. _KIM Items: https://kim-items.openkim.org/kim-items/models/alphabetical/
.. _KIM Properties Framework: https://openkim.org/properties-framework/
.. _at github: https://github.com/openkim/openkim-pipeline/blob/edn/tools/testgenie
.. _this page (FIXME): http://example.com
.. _~/openkim-api/DOCS/standard.kim: https://raw.githubusercontent.com/openkim/openkim-api/v1.5.0/KIM_API/standard.kim
.. _downloads page: https://pipeline.openkim.org/downloads
.. _VirtualBox: https://www.virtualbox.org/
.. _Vagrant: https://www.vagrantup.com/
.. _this Model's KIM Items page: https://openkim.org/cite/MO_142799717516_000
.. _this Test's KIM Items page: https://openkim.org/cite/TE_342002765394_000
