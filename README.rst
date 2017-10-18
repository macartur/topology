########
Overview
########

.. attention::

    THIS NAPP IS STILL EXPERIMENTAL AND IT'S EVENTS, METHODS AND STRUCTURES MAY
    CHANGE A LOT ON THE NEXT FEW DAYS/WEEKS, USE IT AT YOUR OWN DISCERNEMENT

This NApp is responsible for tracking the network topology and supplying
network topology information to any NApp that requires it.

This NApp intends to be protocol agnostic. Therefore, if you want to provide
network topology data from any network protocol, check the listened events
section and generate them from your NApp.

##########
Installing
##########

All of the Kytos Network Applications are located in the NApps online
repository. To install this NApp, run:

.. code:: shell

   $ kytos napps install kytos/topology

###########
Configuring
###########

You can preload your topology by defining, on the `settings.py` file, the
variable `PRELOAD_TOPOLOGY_PATH` with the path of the *json* file you wish to
preload. The format of this json must follow the structure of the
Topology.to_json() method.

######
Events
######

********
Listened
********

.*.switch.new
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
Event reporting that two interfaces were identified as NNI interfaces.

Content
-------

.. code-block:: python3

   {
     'interface_a': {
        'switch': <switch id>,
        'port': <port number>
     },
     'interface_b': {
        'switch': <switch id>,
        'port': <port number>
     }
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

Content
-------

.. code-block:: python3

   {
     'topology': <Topology object>
   }

########
Rest API
########

You can find a list of the available endpoints and example input/output in the
'REST API' tab in this NApp's webpage in the `Kytos NApps Server
<https://napps.kytos.io/kytos/topology>`_.
