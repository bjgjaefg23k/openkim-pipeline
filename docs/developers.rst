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


Test development
----------------
