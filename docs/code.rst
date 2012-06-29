Code
====

Below is some detailed descriptions of the code itself

 * :ref:`config-sec` - holds constants, setups up logging and exceptions
 * :ref:`models-sec` - creates the python object models (~ORM) used throughout
 * :ref:`kimapi-sec` - holds wrapped kim_api calls 
 * :ref:`database-sec` - stand in for queries on the repository, kim_code processing
 * :ref:`rsync_tools-sec` - wrapped rsync commdands
 * :ref:`runner-sec` - runs tests and models together
 * :ref:`template-sec` - handles templating of in and out files
 * :ref:`persistentdict-sec` - useful recipe for handling json info files


.. _config-sec:

config.py
----------------------

`[source code] <_modules/config.html>`_  :download:`[download] <../config.py>`

.. automodule:: config

Constants / Environment Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Of the important constants there are

.. data:: KIM_DIR

which just grabs the environment variable ``KIM_DIR``

.. data:: KIM_API_DIR

which is either the environment variable ``KIM_API_DIR`` if it exists or is assumed to be at ``$KIM_DIR/KIM_API``

.. data:: KIM_REPOSITORY_DIR

grabbed from the environment variable ``KIM_REPOSITORY_DIR``

.. data:: KIM_PIPELINE_DIR

which is just the path of the ``config.py`` file.

.. data:: METADATA_INFO_FILE

The filename for the metadata, currently ``metadata.json``

.. data:: PIPELINE_INFO_FILE

Another pipeline info file filename, currently ``pipelineinfo.json``

.. data:: INPUT_FILE

The name for test input files currently ``pipeline.in``

.. data:: OUTPUT_FILE

The name for the test output file, naming its properties, currently ``pipeline.out``

.. data:: STDOUT_FILE

Captures stdout when the test is run, currently ``pipeline.stdout``

.. data:: TEMP_INPUT_FILE

The name of the processed input file, currently ``pipeline.in.tmp``


Remote Access Settings
^^^^^^^^^^^^^^^^^^^^^^

There are a few settings setup for the remote access, should be changed eventually

.. todo::

    Read from /persistent/username and /persistent/sitename

.. data:: GLOBAL_IP

Will never change, the address you connect to the deamon (localhost because ports are forwarded)

.. data:: GLOBAL_PORT

The port to connect to the deamon on, static

.. data:: GLOBAL_USER

Username for remote address

.. data:: GLOBAL_HOST

machine running the deamon

.. data:: GLOBAL_DIR

Directory on the remote machine in which the repository lives




.. _models-sec:

models.py
----------------------

`[source code] <_modules/models.html>`_ :download:`[download] <../models.py>`

.. automodule:: models
    :members:


.. _kimapi-sec:

kimapi.py
----------------------
.. automodule:: kimapi
    :members:



.. _database-sec:

database.py
---------------------
.. automodule:: database
    :members:



.. _rsync_tools-sec:

rsync_tools.py
-------------------
.. automodule:: rsync_tools
    :members:



.. _pipeline-sec:

pipeline.py
----------------------
.. automodule:: pipeline
    :members:

.. _runner-sec:

runner.py
---------------
.. automodule:: runner
    :members:



.. _template-sec:

template.py
--------------
.. automodule:: template
    :members:



.. _persistentdict-sec:

persistentdict.py
----------------------
.. automodule:: persistentdict
    :members:


