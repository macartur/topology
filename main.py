"""Main module of kytos/topology Kytos Network Application.

Manage the network topology
"""
import json
from pathlib import Path

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
        """Initiate a new topology and preload configurations."""
        self.topology = Topology()
        topology_json = settings.PRELOAD_TOPOLOGY_PATH
        if Path(topology_json.exists()):
            with open(Path(topology_json), 'r') as data:
                data = json.loads(data.read())
                try:
                    self.topology = Topology.from_json(data)
                except Exception:
                    self.topology = Topology()
        else:
            self.topology = Topology()

    def execute(self):
        """Do nothing."""
        pass

    def shutdown(self):
        """Do nothing."""
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

    @listen_to('.*.switch.new')
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

    @listen_to('.*.reachable.mac')
    def set_link(self, event):
        """Set a new link if needed."""
        device_a = self.topology.get_device(event.content['switch'])

        if device_a is None:
            device_a = Device(event.content['switch'])
            self.topology.add_device(device_a)

        if not device_a.has_port(event.content['port']):
            port = Port(number=event.content['port'])
            device_a.add_port(port)

        interface_a = device_a.get_interface_for_port(event.content['port'])

        link = self.topology.get_link(interface_a)
        if link is not None:
            return

        # Try getting one interface for that specific mac.
        mac = event.content['reachable_mac']
        device_b = None
        interface_b = None
        for device in self.topology.devices:
            for port in device.ports:
                if port.mac == mac:
                    interface_b = device.get_interface_for_port(port)

        if interface_b is None:
            device_b = Device(mac, dtype=DeviceType.HOST)
            port = Port(mac=mac)
            device_b.add_port(port)
            self.topology.add_device(device_b)
            interface_b = Interface(device_b, port)

        self.topology.set_link(interface_a, interface_b)

    @listen_to('.*.interface.is.nni')
    def set_interface_as_nni(self, event):
        """Set an existing interface as NNI (and the interface linked to it).

        If the interface is already a NNI, then nothing is done.
        If the interface was not set as NNI, then it will be set and also an
        'kytos.topology.updated' event will be raised.
        Args:
            event (KytosEvent): a dict with interface_a and interface_b keys,
                each one containing switch id and port number.

        """
        interface_a = event.content['interface_a']
        interface_b = event.content['interface_b']

        # Get Switch A
        switch_a = self.topology.get_device(interface_a['switch'])
        if switch_a is None:
            switch_a = Device(switch_a)
            self.topology.add_device(switch_a)

        # Get Port A
        port_a = switch_a.get_port(interface_a['port'])
        if port_a is None:
            port_a = Port(interface_a['port'])
            switch_a.add_port(port_a)

        # Interface A
        interface_a = Interface(switch_a, port_a)

        # Get Switch B
        switch_b = self.topology.get_device(interface_b['switch'])
        if switch_b is None:
            switch_b = Device(switch_b)
            self.topology.add_device(switch_b)

        # Get Port B
        port_b = switch_b.get_port(interface_b['port'])
        if port_b is None:
            port_b = Port(interface_b['port'])
            switch_b.add_port(port_b)

        # Interface A
        interface_b = Interface(switch_b, port_b)

        # Get Link from Interface
        link_a = self.topology.get_link(interface_a)
        link_b = self.topology.get_link(interface_b)

        if link_a is not None and link_a is link_b:
            return

        link = self.topology.set_link(interface_a, interface_b, force=True)
        link.set_nnis()

        # Update interfaces from link as NNI
        self.notify_topology_update()

    def notify_topology_update(self):
        """Send an event to notify about updates on the Topology."""
        name = 'kytos/topology.updated'
        event = KytosEvent(name=name, content={'topology': self.topology})
        self.controller.buffers.app.put(event)
