rsync_tools.py
-------------------
`[source code] <../_modules/rsync_tools.html>`_ :download:`[download] <../../rsync_tools.py>`

Contains a set of convience methods for handing all of our rsyncs.

We are assuming that we will have some remote dedicated machine with four different directories 

 * REAL_READ - the public outward facing repository
 * REAL_WRITE - the place for the pipeline to write new test results
 * TEMP_READ - a place to pull down models under consideration
 * TEMP_WRITE - a place to write verification checks before validation

After this the types of operations the pipeline will do are:

 * reads
       * Director
             * model update
                when the director sees that there is a model to update, he'll have to grab the MO dir from REAL_READ
                the whole `te` tests dir from REAL_READ, and a way to check existing TRs
             * test update
                when the director sees that there is a new test, he'll need the whole `mo` directory from REAL_READ,
                the test dir from REAL_READ and a way to check exising TRs
             * model verification check
                if the director is told to check a new model, he'll need
                the whole VC dir from REAL_READ
                and the model dir from TEMP_READ

      * Worker
            * VC,MO job
                if told to run a VC,MO job, the worker will need any dependencies from REAL_READ,
                the whole VCs dir from REAL_READ
                and the MO dir from TEMP_READ
            * TE,MO job
               if told to run a TE,MO pair, a worker will need, the TE dir from REAL_READ, the MO dir from REAL_READ and any
               required dependencies from REAL_READ

 * writes
       * Director
             None
       * Worker
             * VC,MO job
                when completed, the worker will have to write the VR dir to TEMP_WRITE
             * TE,MO job
                when completed the worker will have to write the TR dir to REAL_WRITE

Config
^^^^^^

.. currentmodule:: rsync_tools

The rsync module has its own set of settings

.. data:: RSYNC_ADDRESS

The address of the rsync host

.. data:: RSYNC_REMOTE_ROOT

root directory on remote for the repo dir

.. data:: RSYNC_FLAGS

some flags for rsync calls

.. data:: RSYNC_LOG_FILE_FLAG

ensures rsync logs in ``logs/rsync.log``

.. data:: TEMP_WRITE_PATH
.. data:: TEMP_READ_PATH
.. data:: REAL_WRITE_PATH
.. data:: REAL_READ_PATH

.. data:: LOCAL_REPO_ROOT

the ``KIM_REPOSITORY_DIR``

Methods
^^^^^^^

.. automodule:: rsync_tools
    :members:

