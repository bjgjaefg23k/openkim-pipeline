Beanstalkd Message Format
=========================

Connecting to beanstalkd
------------------------
In order to connect to beanstalkd, you first must create a tunnel to the daemon using ssh::

    sftp user@pipeline.openkim.org:/keys/id_rsa /local/path/name
    ssh -i /path/to/id_rsa -L14177:localhost:14177 pipeline@pipeline.openkim.org

Then, the beanstalk connect on your local machine can be made using::

    Beanstalk.Connection(host="127.0.0.1", port=14177, connect_timeout=60)

The tubes
---------
As of the most recent edit, these are the tubes employed by the beanstalkd consumers:

    * :ref:`jobs_ref` - the jobs that are to be run by the workers
    * :ref:`results_ref` - the results (runtime, json output, error status, etc) of the runs
    * :ref:`updates_ref` - pokes to the pipeline provided by the website
    * :ref:`errors_ref` - serious failings of the pipeline during job runs
    * :ref:`logs_ref` - a convenient place to get the **full** logs from any of the directors and workers
    * :ref:`tr_ids_ref` - a list of TestResult ids as provided by the website
    * :ref:`vr_ids_ref` - a list of VerificationResult ids as provided by the website

Most are encoded JSON string of a dictionary, though two are plain text.  Read the descriptions following for 
the expected format of messages.


.. _jobs_ref:

jobs
^^^^
These are descriptions of the jobs created by a Director and passed on to the Workers as a JSON string with many parts.  
The ingredients to a job are:

    * *jobid* - the KIMID of the test or verification result id for the worker to use when saving the result
    * *job* - a tuple of (Test,Model) or (Verification{Test,Model}, {Test,Model}) to run
    * *priority* - an internally used priority for the run, not consumed by the Worker
    * *depends* - the dependencies required to complete a certain run.  This is a list of KIMIDs that describe what the Worker needs to download in order to successfully complete a task
    * *status* - whether this is pending or approved task 
    * *child* - UNUSED?


.. _results_ref:

results
^^^^^^^
The results of a particular run are not only rsynced directly back to the repo but are also sent along a tube.
This tube's information contains:

    * *jobid* - the same jobid given to the Worker at first, :ref:`jobs_ref`
    * *job* - same tuple job as posted in :ref:`jobs_ref`
    * *priority* - echoing same as in :ref:`jobs_ref`
    * *results* - the full JSON output string of the run coupling


.. _updates_ref:

updates
^^^^^^^
This tube is where the website posts updates to the models and tests that need to be addressed by the pipeline.
There message format should conform to:

    * *kimid* - any form of the kimid that is recognized by the database such as "somemodelname__MO_1234567891012_000" or "MO_1234567891012_000" or "MO_1234567891012"
    * *priority* - how important this update is.  Can be one of the following strings: 'immediate', 'very high', 'high', 'normal', 'low', 'very low'.
    * *status* - can be one of 'approved' or 'pending' to indicate that this is a verification check or regular update

A sample message would be::

    {'kimid' : 'ex_model__MO_000000000000_000', 'priority' : 'normal', 'status' : 'approved' }

.. _errors_ref:

errors
^^^^^^
This tube contains errors that the website may be curious about.  These are mainly
failed job runs that could be addressed further with manual intervention or reruning.  
The format of these messages is:

    * *jobid* - the same jobid given to the Worker at first, :ref:`jobs_ref`
    * *job* - same tuple job as posted in :ref:`jobs_ref`
    * *priority* - echoing same as in :ref:`jobs_ref`
    * *errors* - the error message coming back from the run


.. _logs_ref:

logs
^^^^
This is a complete log of the activity of the pipeline provided by all Workers and Directors
across the board.  The level of detail is specified by the logging in ``pipeline.py``.  The
messages are as follows:

    * *ipaddr* - the public IP address of the originating message (useful for shutting down rogue servers with iptables
    * *sitename* - the site to which the box connected to get credentials
    * *username* - the box's associated username
    * *boxtype* - whether it is 'worker', 'director', or 'devel'
    * *message* - the logging message as output by the logging module in Python


.. _tr_ids_ref:

tr_ids
^^^^^^
This is a consumable list of TestResult IDs.  It is a **plain text** list, not a dictionary or JSON.  
These are the ids that the Directors supply Workers to assign test results.  It should always be full, 
or the queue will get backed up.

.. _vr_ids_ref:

vr_ids
^^^^^^
This is a consumable list of VerificationResult IDs.  It is **plain text** again.  See :ref:`tr_ids_ref`.
