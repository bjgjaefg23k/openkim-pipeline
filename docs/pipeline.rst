OpenKIM Pipeline
===================

Introduction
------------
The OpenKIM pipeline is the backbone of the computational resources that the KIM 
project will use.  The goal is to provide a reliable provenance for the computational
results that are central to the goals of KIM.  The pipeline will run verification checks
and tests for every model in order to best compare and understand the uses of 
interatomic models.  The results of these tests must be reproducable and their origins
trusted so that it may become a resource to the scientific community.  

In order to do so, we have designed a system that relies on many standard software packages
that allow us to abstract locations and hardware to provide standard computational resources
that have very little overhead to instantiate.  The key ingredients to the project are listed
below.

Virtual Machine
^^^^^^^^^^^^^^^
Hardware (CPUs, memory) have come a long way, as they tend to do.  Recently, virtualization
support has become widely adopted enabling guest machines to run on a host with very little
to no real overhead.  This allows us to make a VM that behaves almost exactly as a typical
host machine.  The VM is key to allowing resources to live on a variety of hardware and in 
varied locations.  They also ensure that the history and versions of results can be traced 
back to a single software version that is frozen in history and can be repeated at any time
down the road.

Network tools
^^^^^^^^^^^^^
We rely on a large set of standard networking tools to allow the resources to live in the
nethers of the internet.  SSH tunnels are employed to limit host dependencies on non-native
port access - ssh is standard on any \*nix system and is highly restricting is configured correctly.  
SFTP allows the transfer of these secure resources via authenticated download - the users
of this system can be greatly restricted for security purposes.  RSYNC is used in the system for
file transfer as well as it transfers only the changes of files to reduce network overhead - this 
is tunneled through ssh for security).  BEANSTALKD is the queue we have chosen for its simplicity
and implementation in C, Python, and Ruby.  

Programming Languages
^^^^^^^^^^^^^^^^^^^^^
We have chosen the Python programming language for its large standard library, ease of development,
large acceptance and community support, and ease of install.  


