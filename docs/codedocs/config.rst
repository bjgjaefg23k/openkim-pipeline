config.py
----------------------

`[source code] <../_modules/config.html>`_  :download:`[download] <../../config.py>`

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

.. data:: RUNNER_TIMEOUT

The maximum time allowed for a test to run

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


Logging
^^^^^^^

The ``config.py`` file also sets up the logging for the rest of the project, through the `logging module <http://docs.python.org/library/logging.html>`_, with logs written to ``logs/pipeline.log`` in a rotating file fashion.

To use, at the top of every project, be sure to rename the logger as a child of the method::

    #e.g. in models.py
    from config import *
    logger = logger.getChild('models')

After that you can log at 5 different levels: (debug,info,warning,error,critical) e.g.::

    logger.debug("This is a debug method with formating: %r", "blah")
    logger.info("This is an info message")
    logger.warning("This is a warning level message about the logger: %r", logger)

etc.


KIM Errors
^^^^^^^^^^

Config also creates a set of errors for error handling

.. autoexception:: InvalidKIMID

.. autoexception:: PipelineResultsError

.. autoexception:: PipelineFileMissing

.. autoexception:: PipelineTimeout

.. autoexception:: PipelineDataMissing

.. autoexception:: PipelineSearchError

.. autoexception:: PipelineTemplateError


