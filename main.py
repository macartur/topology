"""Main module of kytos/topology Kytos Network Application.

Manage the network topology
"""
import json
from pathlib import Path

from kytos.core import KytosEvent, KytosNApp, log, rest
from kytos.core.helpers import listen_to

#from napps.kytos.topology.models import (Device, DeviceType, Interface, Port,
#                                         Topology, Host)

from napps.kytos.topology.models import (Topology, Host)

from napps.kytos.topology import settings


class Main(KytosNApp):
    """Main class of kytos/topology NApp.

    This class is the entry point for this napp.
    """

    def setup(self):
        """Initiate a new topology and preload configurations."""
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
        return self.topology.to_json()

    @listen_to('.*.switch.new')
    def handle_new_switch(self, event):
        """Create a new Device on the Topology.

        Handle the event of a new created switch and instantiate a new Device
        on the topology.

        """
        switch = event.content['switch']
        switch.id_ = switch.id
        self.topology.add_device(switch)
        log.debug('Switch %s added to the Topology.', switch.id)
        self.notify_topology_update()

    #@listen_to('.*.switch.port.created')
    #def handle_port_created(self, event):
    #    """Listen an event and create the respective port, if needed."""
    #    device = self.topology.get_device(event.content['switch'])
    #    if device is None:
    #        return

    #    port = device.get_port(event.content['port'])
    #    if port is not None:
    #        msg = 'The port %s already exists on the switch %s. '
    #        msg += 'It cannot be created again.'
    #        log.debug(msg, event.content['port'], device.id_)
    #        return

    #    port = Port(number=event.content['port'])
    #    port.properties = event.content['port_description']
    #    if 'mac' in port.properties:
    #        port.mac = port.properties['mac']
    #    if 'alias' in port.properties and port.properties['alias']:
    #        port.alias = port.properties['alias']
    #    device.add_port(port)

    @listen_to('.*.switch.interface.modified')
    def handle_interface_modified(self, event):
        """Update port properties based on a Port Modified event."""
        # Get Switch
        interface = event.content['interface']
        # TODO: Fix here
        log.info("**********************")
        log.info(interface)

        #device = self.topology.get_device(event.content['switch'])
        #if device is None:
        #    log.error('Device %s not found.', event.content['switch'])
        #    return

        ## Get Switch Port
        #port = device.get_port(event.content['port'])
        #if port is None:
        #    msg = 'Port %s not found on switch %s. Creating new port.'
        #    log(msg, event.content['port'], device.id_)
        #    self.handle_port_created(event)
        #    return

        #port.properties = event.content['port_description']
        #if 'mac' in port.properties:
        #    port.mac = port.properties['mac']

    @listen_to('.*.switch.interface.deleted')
    def handle_interface_deleted(self, event):
        """Delete a port from a switch.

        It also does the necessary cleanup on the topology.

        """
        # Get Switch
        interface = event.content['interface']
        self.topology.remove_interface_links(interface.id)

    @listen_to('.*.reachable.mac')
    def add_host(self, event):
        """Set a new link if needed."""

        interface = event.content['port']
        mac = event.content['reachable_mac']

        host = Host(mac)
        link = self.topology.get_link(interface.id)
        if link is not None:
            return

        self.topology.add_link(interface.id, host.id)
        self.topology.add_device(host)

        if settings.DISPLAY_FULL_DUPLEX_LINKS:
            self.topology.add_link(host.id, interface.id)

    @listen_to('.*.interface.is.nni')
    def add_links(self, event):
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

        self.topology.remove_interface_links(interface_a.id)
        self.topology.remove_interface_links(interface_b.id)

        self.topology.add_link(*sorted([interface_a.id, interface_b.id]))
        if settings.DISPLAY_FULL_DUPLEX_LINKS:
            self.topology.add_link(*sorted([interface_b.id, interface_a.id],
                                           reverse=True))

        interface_a.nni = True
        interface_b.nni = True

        # Update interfaces from link as NNI
        self.notify_topology_update()

    def notify_topology_update(self):
        """Send an event to notify about updates on the Topology."""
        name = 'kytos/topology.updated'
        event = KytosEvent(name=name, content={'topology': self.topology})
        self.controller.buffers.app.put(event)
