
OpenKIM vagrant box
===================

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

But there are simpler ways as well.  

