"""Main module of kytos/topology Kytos Network Application.

Manage the network topology
"""
import json

from kytos.core import KytosEvent, KytosNApp, log, rest
from kytos.core.helpers import listen_to

from napps.kytos.topology.models import (Device, DeviceType, Interface, Port,
                                         Topology)
from napps.kytos.topology import settings


class Main(KytosNApp):
    """Main class of kytos/topology NApp.

    This class is the entry point for this napp.
    """

    def setup(self):
        """Replace the '__init__' method for the KytosNApp subclass.

        The setup method is automatically called by the controller when your
        application is loaded.

        So, if you have any setup routine, insert it here.
        """
        self.topology = Topology()

    def execute(self):
        """Execute right after the setup method execution.

        You can also use this method in loop mode if you add to the above setup
        method a line like the following example:

            self.execute_as_loop(30)  # 30-second interval.
        """
        pass

    def shutdown(self):
        """Execute when your napp is unloaded.

        If you have some cleanup procedure, insert it here.
        """
        log.info('NApp kytos/topology shutting down.')

    @rest('devices')
    def get_device(self):
        """Return a json with all the devices in the topology.

        Responsible for the /api/kytos/topology/devices endpoint.

        e.g. [<list of devices>]

        Returns:
            string: json with all the devices in the topology

        """
        return json.dumps([device.to_json()
                           for device in self.topology.devices])

    @rest('links')
    def get_links(self):
        """Return a json with all the links in the topology.

        Responsible for the /api/kytos/topology/links endpoint.

        Returns:
            string: json with all the links in the topology.

        """
        return json.dumps([link.to_json() for link in self.topology.links])

    @rest('')
    def get_topology(self):
        """Return full topology.

        Responsible for the /api/kytos/topology endpoint.

        Returns:
            string: json with the full topology.

        """
        return json.dumps(self.topology.to_json())

    @listen_to('.*.switch(es)?.new')
    def handle_new_switch(self, event):
        """Create a new Device on the Topology.

        Handle the event of a new created switch and instantiate a new Device
        on the topology.

        """
        switch = event.content['switch']
        device = Device(switch.id)
        self.topology.add_device(device)
        log.debug('Switch %s added to the Topology.', device.id_)
        self.notify_topology_update()

    @listen_to('.*.switch.port.created')
    def handle_port_created(self, event):
        """Listen an event and create the respective port, if needed."""
        device = self.topology.get_device(event.content['switch'])
        if device is None:
            return

        port = device.get_port(event.content['port'])
        if port is not None:
            msg = 'The port %s already exists on the switch %s. '
            msg += 'It cannot be created again.'
            log.debug(msg, event.content['port'], device.id_)
            return

        port = Port(number=event.content['port'])
        port.properties = event.content['port_description']
        if 'mac' in port.properties:
            port.mac = port.properties['mac']
        if 'alias' in port.properties and port.properties['alias']:
            port.alias = port.properties['alias']
        device.add_port(port)

    @listen_to('.*.switch.port.modified')
    def handle_port_modified(self, event):
        """Update port properties based on a Port Modified event."""
        # Get Switch
        device = self.topology.get_device(event.content['switch'])
        if device is None:
            log.error('Device %s not found.', event.content['switch'])
            return

        # Get Switch Port
        port = device.get_port(event.content['port'])
        if port is None:
            msg = 'Port %s not found on switch %s. Creating new port.'
            log(msg, event.content['port'], device.id_)
            self.handle_port_created(event)
            return

        port.properties = event.content['port_description']
        if 'mac' in port.properties:
            port.mac = port.properties['mac']

    @listen_to('.*.switch.port.deleted')
    def handle_port_deleted(self, event):
        """Delete a port from a switch.

        It also does the necessary cleanup on the topology.

        """
        # Get Switch
        device = self.topology.get_device(event.content['switch'])
        if device is None:
            log.error('Device %s not found.', event.content['switch'])
            return

        # Get Switch Port
        port = device.get_port(event.content['port'])
        if port is None:
            msg = 'Port %s not found on switch %s. Nothing to delete.'
            log(msg, event.content['port'], device.id_)
            return

        # Create the interface object
        interface = Interface(device, port)

        # Get Link from Interface
        link = self.topology.get_link(interface)

        # Destroy the link
        self.topology.unset_link(link)

        # Remove the port
        device.remove_port(port)

    @listen_to('.*.interface.is.nni')
    def set_interface_as_nni(self, event):
        """Set an existing interface as NNI (and the interface linked to it).

        If the interface is already a NNI, then nothing is done.
        If the interface was not set as NNI, then it will be set and also an
        'kytos.topology.updated' event will be raised.
        Args:
            event (KytosEvent): a dict with switch id and port number.

        """
        # Get Switch
        switch = self.topology.get_device(event.content['switch'])
        if switch is None:
            return

        # Get Switch Port
        port = switch.get_port(event.content['port'])
        if port is None:
            return

        # Create the interface object
        interface = Interface(switch, port)

        # Get Link from Interface
        link = self.topology.get_link(interface)
        if link is None:
            return

        # If both interfaces are set as NNI, there is nothing to be done.
        if link.interface_one.is_nni() and link.interface_two.is_nni():
            return

        # Update interfaces from link as NNI
        link.interface_one.set_as_nni()
        link.interface_two.set_as_nni()
        self.notify_topology_update()

    def notify_topology_update(self):
        """Send an event to notify about updates on the Topology."""
        name = 'kytos.topology.updated'
        event = KytosEvent(name=name, content={'topology': self.topology})
        self.controller.buffers.app.put(event)
