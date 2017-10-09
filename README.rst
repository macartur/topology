########
Overview
########

.. attention::

    THIS NAPP IS STILL EXPERIMENTAL AND IT'S EVENTS, METHODS AND STRUCTURES MAY
    CHANGE A LOT ON THE NEXT FEW DAYS/WEEKS, USE IT AT YOUR OWN DISCERNEMENT

This NApp is responsible for tracking the network topology and supply it to any
NApp that requires it.

##########
Installing
##########

All of the Kytos Network Applications are located in the NApps online
repository. To install this NApp, run:

.. code:: shell

   $ kytos napps install kytos/topology

######
EVENTS
######

********
Listened
********

.*.switch(es)?.new
==================
Event reporting that a new switch was created/added on the network.

Content
-------

.. code-block:: python3

   {
     'switch': <Switch object>  # kytos.core.switch.Switch class
   }

.*.switch.port.created
======================
Event reporting that a port was created/added in the switch/datapath.

Content
-------

.. code-block:: python3

   {
     'switch': <switch id>,
     'port': <port number>,
     'port_description': {<description of the port>}  # port description dict
   }

.*.switch.port.modified
=======================
Event reporting that a port was modified in the datapath.

Content
-------

.. code-block:: python3

   {
     'switch': <switch id>,
     'port': <port number>,
     'port_description': {<description of the port>}  # port description dict
   }

.*.switch.port.deleted
======================
Event reporting that a port was deleted from the datapath.

Content
-------

.. code-block:: python3

   {
     'switch': <switch id>,
     'port': <port number>,
     'port_description': {<description of the port>}  # port description dict
   }

.*.interface.is.nni
===================
Event reporting that a interface is a NNI interface.

Content
-------

.. code-block:: python3

   {
     'switch': <switch id>,
     'port': <port number>
   }

.*.reachable.mac
================
Event reporting that a mac address is reachable from a specific switch/port.

Content
-------

.. code-block:: python3

    {
        'switch': <switch id>,
        'port': <port number>,
        'reachable_mac': <mac address>
    }

*********
Generated
*********

kytos/topology.updated
======================
Event reporting that the topology was updated. It contains the most updated
topology.

The ``topology object``.

Content
-------

.. code-block:: python3

   {
     'devices': [<list_of_devices>],
     'links': [<list_of_links_between_interfaces>]
   }
