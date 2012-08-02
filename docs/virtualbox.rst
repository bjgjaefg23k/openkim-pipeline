
Virtual Machine
===================
Hardware (CPUs, memory) have come a long way, as they tend to do.  Recently, virtualization
support has become widely adopted enabling guest machines to run on a host with very little
to no real overhead.  This allows us to make a VM that behaves almost exactly as a typical
host machine.  The VM is key to allowing resources to live on a variety of hardware and in 
varied locations.  They also ensure that the history and versions of results can be traced 
back to a single software version that is frozen in history and can be repeated at any time
down the road.


Creating a development or worker box
------------------------------------

To get it out of the way, the most important things are to create a development box
or a director/worker box.  To create either, you must first acquire the
``Vagrantfile`` as found in::

    openkim-pipeline-setup/static/foruser/Vagrantfile

Copy this to a new directory and run ``vagrant up``.  That's it!

If you wish to make the box secure, you must also acquire::

   openkim-pipeline-setup/static/foruser/secure

Copy this to the current directory and run it with ``./secure``.  It will then
ask you your four favorite questions::

    Worker or director?
    Sitename (openkim.org, purdue.openkim.org, etc)
    Username
    Password

After this, it will proceed to shut the box down to outside influences and become 
a worker.  That's it!  What follows is a technical description of how that happens. 


Introduction to vagrant
-----------------------
Vagrant is a ruby wrapper around VirtualBox, a VM environment produced by 
Oracle which is available across most platforms.  It allows you to package
a 'box' (basically a compressed VB image) and ship it out to others.  On top
of this, there is a flexible provisioning framework provided by shell scripts,
Chef, and Puppet provisioners which install all of the necessary software on
top of a base box.

Once you have a vagrant.box file, to start it up you would run::
    
    vagrant box add someboxname vagrant.box
    vagrant init someboxname
    vagrant up

But there are simpler ways as well. For example, you can provide a Vagrantfile which
contains directives for where the .box file is found and how to provision it.  We use
this method in the pipeline.  This lines in the Vagrantfile look like this::

    config.vm.box = "openkim"
    config.vm.box_url = "http://server.org/openkim.box"

Now, if you were to make an empty directory, copy the Vagrantfile into the directory and
run ``vagrant up``, a bunch magic would happen where vagrant downloads, decompresses
and installs the box, then boots it up.

To log on to the box after we initialize it, run::

    vagrant ssh

and then to shutdown the box, run::

    vagrant halt

This will simply shutdown the box as if you have pressed the power button on a real 
computer.  If you wish to restart from a fresh box, you would run::

    vagrant destroy

and the box would come back just as you had downloaded it. After you have made changes to 
the box and would like to ship it out again, you should ``halt`` the box and then
run::

    vagrant package

which creates a file ``package.box`` which you can then share.


Features of our box
--------------------
We are running a Ubuntu Precise 64bit distribution that has a lot of base software
installed.  This includes many python packages (scipy, numpy, pylab, ipython, 
beanstalkc come to mind) and base software (build-essential, gfortran, sshd, etc).

The entire install is made on an LVM (logical volume manager) which abstracts
hardware (disks like ``/dev/sda``) from software partitions (``/dev/mapper/vg0-root``). 
The structure is that a volume group (VG) is build around many different physical
resources (PV).  In this VG, there are many logical volumes (LV) which act like
filesystems just as you would expect a partition to behave.  Our VG is vagrant-pipeline,
and it contains 4 LVs and 1 real partition.  They are: 1) ``root``, where are system is installed 2) ``persistent``
a small, but persistent partition 3) ``swap``, obvious and 4) ``root_snap`` and LVM2 snapshot
of the root partition. The real partition is ``/dev/sda1`` and is mounted at ``/boot`` so that
it is always persistent.

When the box is run, the file ``/boot/grub/grub.cfg`` specifies that indeed the ``root_snap`` 
LV is used at the root filesystem for our box.  The actual ``root`` is never mounted when
not being used for development by the box maintainer.  

To ensure that provisioning runs as expected and that the box has the capability of resnapping
itself, there are some files that are special on top of the base ubuntu system.

Boot files
^^^^^^^^^^
At the core, the initrd (initial ramdisk) for the system has been modified.  We added a new
``local-premount`` script called ``resnap`` which looks for the flag ``resnap`` passed along
by the grub bootloader.  If this flag is present then the old snapshot is thrown away and 
recreated before the root filesystem is mounted.  This will ensure that all changes made
to the box are destroyed.

This means that the grub bootloader has been modified as well.  In particular, there are several
new command line arguments to vmlinuz::
    
    volgroup=vagrant-pipeline
    lvroot=root
    lvsnap=root_snap
    lvsize=45G
    resnap

The first four arguments tell the new initrd how to take the snapshot while the last one, ``resnap``
actually tells it to take action upon booting.

The new grub line now looks like::

    linux   /vmlinuz-3.2.0-23-generic root=/dev/mapper/vagrant--pipeline-root_snap ro volgroup=vagrant-pipeline lvroot=root lvsnap=root_snap lvsize=45G [resnap]
    
This also means that everytime the kernel is updated, the initrd must be regenerated since it is
customized.  There is a script provided in ``openkim-pipeline-setup/static/makeinitrd`` that 
will do this automatically.


provisiond Init Daemon
^^^^^^^^^^^^^^^^^^^^^^
Since the system comes up fresh again on reboot when provided the ``resnap`` option, we need a way
to reinstall the entire system even when we don't have ssh access.  To do this, there is a new "daemon"
that runs every time the system is started.  It checks the file ``/proc/cmdline`` (which contains the same
grub command line options given to the initrd) for the word ``resnape``.  If it is there then
it runs the last two pieces of software which are necessary for the box...


Static Setup Scripts
^^^^^^^^^^^^^^^^^^^^
There are two scripts that should be located in the ``/persistent`` directory.  They are called
``runsetup`` and ``runsecure``.  The first script grabs the lastest stable branch of 
openkim-pipeline-setup and runs its setup file.  The second script runs the secure script from
the same git repository.  These are also run when the user runs ``vagrant up`` for the first time
when starting the box.  These shouldn't need to be changed ever (except maybe the git url).


Vagrant provisioning
--------------------
To get the box how we like it, we are using the Shell provisioner.  It is simply
a series of bash scripts that have been tested to acquire software and install it
from a large variety of sources.  The main scripts are ``setup`` and ``secure``
which run the development base setup and make the base headless and secure respectively.

These shell scripts are run through ``/persistent/runsetup`` and ``/persistent/runsecure``
and are run at various times throughout the life of a pipeline box.  

For their details, see the code.  They are rather simple and short.

File dependencies
^^^^^^^^^^^^^^^^^
There are a number of files that are acquired over the network to ensure that provisioning
occurs as planned.  Currently (as of 29/06/2012) they are:

* *openkim-pipeline-setup.git* : the first thing pulled. Grabs the rest of the items
* *openkim-api.git* : pulls a given checkout of the openkim API
* *openkim-python.git* : the python interface to the KIM API
* *openkim-kimcalculator-ase.git* : the ASE interface to KIM
* *openkim-repository.git* : a bunch of sample models
* *openkim-pipeline.git* : the pipeline runner code.  creates workers and directors
* *ase* : the Atomic Simulation Environment, a Python atomistic simulation code
* *lammps* : a binary executable that has been built for the virtual box 


Debugging setup scripts
^^^^^^^^^^^^^^^^^^^^^^^
After making changes to the setup scripts, you should check to make sure that they
set the system up as you expect.  One of approaching this is to boot into a fresh
VM and comment out the provisioning from the ``Vagrantfile``.  This involves
putting a "#" in the beginning of the inline directive::

    config.vm.provision :shell, :inline => "/persistent/runsetup <hostname>"

goes to::

    config.vm.provision :shell, :inline => "#/persistent/runsetup <hostname>"

Then ssh into the box as normal, download your working version of the setup scripts
from the correct source and try them out.  

It is also possible to change the working branch from which the scripts are 
downloaded.  In particular, the second option to runsetup accepts a branch
name.  The default value is ``stable``, but can be replaced by any other branch
such as master.  This will allow you to easily run through the entire setup process
including authorizing a worker to see if it comes up properly.  The line
listed above now becomes::

    config.vm.provision :shell, :inline => "/persistent/runsetup <hostname> <otherbranch>"


Modifying the base box
----------------------
If you would like to boot into ``root`` in order to make persistent changes to the 
virtualbox, you would need to change the root directive in ``/boot/grub/grub.cfg`` from:: 

    root=/dev/mapper/vagrant--pipeline-root_snap 

to::

    root=/dev/mapper/vagrant--pipeline-root 

This will cause the box to boot into the correct logical volume.  From there, you can make
your changes and repackage the box.  Before you do so, however, you need to reconfigure the
essentials of the box.  **There is a script provided for this** inside ``openkim-pipeline-setup/static``
that does most of the work for you. 


Size issues
-----------
The box will naturally inflate in actual disk usage on the host over time.  The swap will be
used, the files created and destroyed never really get cleaned up.  If you wish to shrink
the box down to reasonable sizes again, simply run::

    sudo /home/vagrant/shrink

This creates a huge file full of zeros and then deletes it.  It helps, trust me.


