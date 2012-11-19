Gateway machine
===============
The link between the webserver and the pipeline is mediated by a machine (currently managed on Amazon EC2) 
called the gateway.  This machine contains a local copy of the repository, various file dependencies that
are required by the setup scripts for directors/workers, the beanstalk daemon, a gateway daemon, and
all of the authentication materials for the directors/workers.

Organization
------------
The only direct login to the machine is the user ``ubuntu`` which can be accessed through the pem keys
as distributed through Amazon EC2.  This is the user that is responsible for the beanstalkd and gatewayd
as well. 

The owner of ``/repository`` and ``/repository_dbg`` is the user pipeline in order to separate the privileges 
on the system - i.e. the rsync user cannot read the ecdsa key needed to access the repository.
The only way to become the pipeline user is to ``sudo su pipeline``
from the ubuntu user or to login via ssh with a key.  However, when logging in through ssh, the shell is
restricted to rsync_only so the only real way is through the Amazon account.  

The ubuntu user owns the beanstalkd and gateway processes.  They are launched through scripts 
from the ubuntu user account.  During typical operation, pipeline's home folder is completely blank
while ubuntu's home folder contains the scripts that launch the various important processes::

    drwxr--r-- 2 ubuntu ubuntu 4.0K Nov  8 23:17 beanlog
    drwxr--r-- 2 ubuntu ubuntu 4.0K Nov  8 23:17 beanlog_dbg
    drwxr--r-- 3 ubuntu ubuntu 4.0K Nov  8 23:12 gateway
    -rw------- 1 ubuntu ubuntu  365 Nov  7 19:59 id_ecdsa_pipeline
    -rwxr--r-- 1 ubuntu ubuntu 1.2K Aug 20 14:50 makeuser.sh
    -rwxr--r-- 1 ubuntu ubuntu  250 Nov  8 23:16 startdaemon.sh
    -rwxr--r-- 1 ubuntu ubuntu  146 Nov  8 23:07 startgateway.sh

These launch both the beanstalkd and gatewayd for production and debug modes.  A typical screen
of the ubuntu user should look like::

    ubuntu@pipeline.openkim.org:~$ screen -r
    There are several suitable screens on:
        21005.gateway_dbg   (11/06/2012 11:44:24 PM)    (Detached)
        21002.gateway   (11/06/2012 11:44:24 PM)    (Detached)
        7843.beanstalkd_dbg (11/06/2012 09:53:40 PM)    (Detached)
        7831.beanstalkd (11/06/2012 09:53:40 PM)    (Detached)
    Type "screen [-d] -r [pid.]tty.host" to resume one of them.

Finally, the files that are essential for the openkim-pipeline-setup scripts are located in the apache root,
along with the documentation you are currently reading.  Excluding this documentation, the ``/var/www`` contains::

    ubuntu@:/var/www$ ls -lh vm
    total 1.2G
    -rw-r--r-- 1 ubuntu ubuntu 564M Aug  2 19:31 openkim20120802.box
    -rw-r--r-- 1 root   root   564M Aug 31 00:08 openkim.box

    ubuntu@:/var/www$ l packages/
    total 12K
    drwxr-xr-x 2 ubuntu ubuntu 4.0K Aug  6 15:08 ase
    drwxrwxr-x 2 ubuntu ubuntu 4.0K Sep  3 16:22 lammps
    drwxrwxr-x 2 ubuntu ubuntu 4.0K Oct  2 21:11 unixbench

    ubuntu@:/var/www$ l packages/*
    packages/ase:
    total 708K
    -rw-r--r-- 1 ubuntu ubuntu 708K Feb 24  2012 python-ase-3.6.0.2515.tar.gz
    
    packages/lammps:
    total 720K
    -rw-rw-r-- 1 ubuntu ubuntu 717K Sep  3 16:21 lammps_serial_kim.20120903.tar.gz
    
    packages/unixbench:
    total 144K
    -rw-rw-r-- 1 ubuntu ubuntu 141K Oct  2 21:10 unixbench-5.1.2.tar.gz

As of the time of writing (07/10/2012).

These scripts found in both of the user home folders can be found 
`here <https://github.com/openkim/openkim-pipeline-setup/tree/master/static/daemonbox>`_ 
while the scripts that give a sense of how the EC2 box was initially setup can be found
`here <https://github.com/openkim/openkim-pipeline-setup/tree/master/static/daemonbox/setup>`_.
It should be noted that this script is very vague at the moment, so it is more useful
to read it than to run it.  


Authorization
-------------
Public keys are the primary means of authentication.  Typically these allow anyway to go nutso on your system though.
To restrict them, we use a very restricted shell that we call ``rsync_only`` which denies any commands to be run
aside from rsync, and a configured ``authorized_keys`` file which limits connections to port forwarding.  An example is provided
here for posterity::

    command="/usr/local/bin/rsync_only.sh",permitopen="127.0.0.1:14176",permitopen="127.0.0.1:14177",no-X11-forwarding,no-agent-forwarding,no-pty,no-user-rc ecdsa-sha2-nistp521 <snip> pipeline@pipeline.openkim.org


Creating accounts
-----------------
It is very simple to create a new user account for a director/worker.  Simply run ``makeuser.sh`` as 
the ubuntu user and you will be prompted for a username and password.  Everything else will be done for you.
