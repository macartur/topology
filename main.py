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
    def get_devices(self):
        """Return a json with all the devices in the topology.

        For now, a device can be a Switch or a Host.
        """
        out = {'devices': {d.id: d.as_dict() for d in self.topology.devices}}
        return json.dumps(out)

    @rest('links')
    def get_links(self):
        """Return a json with all the links in the topology.

        Links are directed connections between devices.
        """
        links = []
        for link in self.topology.links:
            links.append({'source': link[0], 'target': link[1]})

        return json.dumps({'links': links})

    @rest('/')
    def get_topology(self):
        """Return the latest known topology.

        This topology is updated when there are network events.
        """
        return self.topology.to_json()

    @listen_to('.*.switch.new')
    def handle_new_switch(self, event):
        """Create a new Device on the Topology.

        Handle the event of a new created switch and update the topology with
        this new device.
        """
        switch = event.content['switch']
        switch.id_ = switch.id
        self.topology.add_device(switch)
        log.debug('Switch %s added to the Topology.', switch.id)
        self.notify_topology_update()

    @listen_to('.*.switch.interface.modified')
    def handle_interface_modified(self, event):
        """Update the topology based on a Port Modified event.

        If a interface is with state down or similar we remove this interface
        link from the topology.
        """
        # Get Switch
        interface = event.content['interface']
        # TODO: Fix here
        log.info("**********************")
        log.info(interface)

    @listen_to('.*.switch.interface.deleted')
    def handle_interface_deleted(self, event):
        """Update the topology based on a Port Delete event."""
        # Get Switch
        interface = event.content['interface']
        self.topology.remove_interface_links(interface.id)

    @listen_to('.*.reachable.mac')
    def add_host(self, event):
        """Update the topology with a new Host."""

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
        """Update the topology with links related to the NNI interfaces."""
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
        """Send an event to notify about updates on the topology."""
        name = 'kytos/topology.updated'
        event = KytosEvent(name=name, content={'topology': self.topology})
        self.controller.buffers.app.put(event)
