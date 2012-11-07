Pipeline Maintainer
===================
The information presented here is intended for the people responsible for maintaining
the systems that keep the pipeline running.  This includes updating the VM itself,
changing around the provisioning scripts, modifying the pipeline python scripts, and
dealing with the gateway and EC2 setup.  I will go in order from the very low level
parts to the very high level.

Modifying the base box
----------------------
In order to update the kernel, do an upgrade of the OS or affect anything about the
virtual machine that cannot be changed while the machine is running (changing disk
size also comes to mind and may be relevant) then you must apply these to the
true root filesystem.  

If you would like to boot into ``root`` in order to make persistent changes to the 
virtualbox, you would need to change the root directive in ``/boot/grub/grub.cfg`` from:: 

    root=/dev/mapper/vagrant--pipeline-root_snap 

to::

    root=/dev/mapper/vagrant--pipeline-root 

This will cause the box to boot into the correct logical volume.  From there, you can make
your changes and repackage the box.  Before you do so, however, you need to reconfigure the
essentials of the box.  **There is a script provided for this** inside ``openkim-pipeline-setup/static``
that does most of the work for you (located `here <https://github.com/openkim/openkim-pipeline-setup/tree/stable/static>`_). 

The first relevant script is located in ``makeinitrd/makeinitrd.sh``.  This script attempts to 
unpack the initrd.img used by the current kernel, add the approach resnap commands to the
local-premount scripts and then updates grub to setup the necessary boot parameters.

Next, ``finalizebox`` should be run.  This scripts attempts to copy the necessary ``onbox`` files 
to the appropriate locations, shrinks the filesystem as much as possible, then creates a snapshot
of the appropriate size.  If you change the size of the disk, you need to change it here as well 
(and anywhere else there is a reference to ``LVSIZE``).   After running this script, you should
delete everything from the ``vagrant`` user's home directory except the ``shrink`` script. 


Debugging openkim-pipeline-setup scripts
----------------------------------------
The next important level to the system is openkim-pipeline-setup which setups the 
software environment that lives on top of the base OS.  It is important that
these scripts are success or it may brick every running box (due to crontab jobs
which search for updates to the github via this `script <https://github.com/openkim/openkim-pipeline-setup/blob/master/checkup>`_). 

After making changes to the setup scripts, you should check to make sure that they
set the system up as you expect.  The preferred method is to change the working branch from which the scripts are 
downloaded.  In particular, the second option to runsetup accepts a branch
name.  The default value is ``stable``, but can be replaced by any other branch
such as master.  This will allow you to easily run through the entire setup process
including authorizing a worker to see if it comes up properly.  The line
listed above now becomes::

    config.vm.provision :shell, :inline => "/persistent/runsetup <hostname> <otherbranch>"

for example::
    
    config.vm.provision :shell, :inline => "/persistent/runsetup github.com/openkim master" 

After running ``vagrant up``, you can check to make sure that the system is how you expect.
If it is successful, you can them merge the test branch into ``stable`` which is automatically
checked by workers and directors for changes.  After 24 hours, every box should reflect the
most recent changes.

Another approaching is to boot into a fresh
VM and comment out the provisioning from the ``Vagrantfile``.  This involves
putting a "#" in the beginning of the inline directive::

    config.vm.provision :shell, :inline => "/persistent/runsetup <hostname>"

goes to::

    config.vm.provision :shell, :inline => "#/persistent/runsetup <hostname>"

Then ssh into the box as normal, download your working version of the setup scripts
from the correct source and try them out.  


Debugging openkim-pipeline 
--------------------------
Modifying the openkim-pipeline scripts is safer than editing the setup scripts.  If these fail on the production
system, they only need to be modified and the setup scripts changed to force a repull.  It will however
result in 24 hours of downtime, so be careful nonetheless.  

In order to accomodate easier debugging, there is a parallel gateway and beanstalkd in place that mimick
the production system.  To employ this debug system, the environment variable ``PIPELINE_DEBUG`` should be 
set to any value.  This causes the beanstalkd queue port to be changed from 14177 to 14176 and the
write directory to change from ``results`` to ``debug``.  This environment variable and more are created when
a virtual machine is made secure as a type ``devel``.  This is not a publicized option in the secure scripts
but trust me, it's there. 

Once you have made sufficient changes to the pipeline running scripts, you need to push the changes to
the running production environment.  To do so, modify the hash found in ``openkim-pipeline-setup/setup-openkim-pipeline/setup-openkim-pipeline.sh`` to reflect the current commit on the master branch.  It is often prudent to only modify the 
master branch of openkim-pipeline-setup, test that it can initialize a box correctly, then 
merge it with stable.  The merge when then ensure that the production boxes will gather the 
correct pipeline within 24 hours.


Modifying the gateway
---------------------
Currently, the gateway is not separated in a clean way for production and debug systems.  It is recommended
to simply take down gateway_dbg temporarily, modify the gateway scripts, then run the ``python gateway.py dbg``
from the command line until it is working how you desire.  Then, kill both gateways and reinitialize them from
the ubuntu user home.
