"""Main module of kytos/topology Kytos Network Application.

Manage the network topology
"""
from flask import jsonify
from kytos.core import KytosEvent, KytosNApp, log, rest
from kytos.core.helpers import listen_to
from kytos.core.link import Link

from napps.kytos.topology import settings


class Main(KytosNApp):
    """Main class of kytos/topology NApp.

    This class is the entry point for this napp.
    """

    def setup(self):
        """Initialize the NApp's links list."""
        self.links = []

    def execute(self):
        """Do nothing."""
        pass

    def shutdown(self):
        """Do nothing."""
        log.info('NApp kytos/topology shutting down.')

    def _get_link_or_create(self, endpoint_a, endpoint_b):
        new_link = Link(endpoint_a, endpoint_b)
        if new_link not in self.links:
            self.links.append(new_link)
            return new_link

        for link in self.links:
            if link == new_link:
                return link

    def _get_switches_dict(self):
        """Return a dictionary with the known switches."""
        return {'switches': {d.id: d.as_dict() for d in
                             self.controller.switches.values()}}

    def _get_links_dict(self):
        """Return a dictionary with the known links."""
        links = {}
        for link in self.links:
            links[link.id] = link.as_dict()

        return {'links': links}

    def _get_topology_dict(self):
        """Return a dictionary with the known topology."""
        return {'topology': {**self._get_switches_dict(),
                             **self._get_links_dict()}}

    @rest('v2/switches')
    def get_switches(self):
        """Return a json with all the switches in the topology."""
        return jsonify(self._get_switches_dict())

    @rest('v2/interfaces')
    def get_interfaces(self):
        """Return a json with all the interfaces in the topology."""
        interfaces = {}
        switches = self._get_switches_dict()
        for switch in switches['switches'].values():
            for interface_id, interface in switch['interfaces'].items():
                interfaces[interface_id] = interface

        return jsonify({'interfaces': interfaces})

    @rest('v2/links')
    def get_links(self):
        """Return a json with all the links in the topology.

        Links are connections between interfaces.
        """
        return jsonify(self._get_links_dict())

    @rest('v2/')
    def get_topology(self):
        """Return the latest known topology.

        This topology is updated when there are network events.
        """
        return jsonify(self._get_topology_dict())


    @listen_to('.*.switch.(new|reconnected)')
    def handle_new_switch(self, event):
        """Create a new Device on the Topology.

        Handle the event of a new created switch and update the topology with
        this new device.
        """
        switch = event.content['switch']
        switch.active = True
        log.debug('Switch %s added to the Topology.', switch.id)
        self.notify_topology_update()

    @listen_to('.*.connection.lost')
    def handle_connection_lost(self, event):
        """Remove a Device from the topology.

        Remove the disconnected Device and every link that has one of its
        interfaces.
        """
        switch = event.content['source'].switch
        if switch:
            switch.active = False
            log.debug('Switch %s removed from the Topology.', switch.id)
            self.notify_topology_update()

    @listen_to('.*.switch.interface.up')
    def handle_interface_up(self, event):
        """Update the topology based on a Port Modify event.

        The event notifies that an interface was changed to 'up'.
        """
        interface = event.content['interface']
        interface.active = True
        self.notify_topology_update()

    @listen_to('.*.switch.interface.created')
    def handle_interface_created(self, event):
        """Update the topology based on a Port Create event."""
        self.handle_interface_up(event)

    @listen_to('.*.switch.interface.down')
    def handle_interface_down(self, event):
        """Update the topology based on a Port Modify event.

        The event notifies that an interface was changed to 'down'.
        """
        interface = event.content['interface']
        interface.active = False
        self.handle_interface_link_down(event)
        self.notify_topology_update()

    @listen_to('.*.switch.interface.deleted')
    def handle_interface_deleted(self, event):
        """Update the topology based on a Port Delete event."""
        self.handle_interface_down(event)

    @listen_to('.*.switch.interface.link_up')
    def handle_interface_link_up(self, event):
        """Update the topology based on a Port Modify event.

        The event notifies that an interface's link was changed to 'up'.
        """
        interface = event.content['interface']
        if interface.link:
            interface.link.active = True
        self.notify_topology_update()

    @listen_to('.*.switch.interface.link_down')
    def handle_interface_link_down(self, event):
        """Update the topology based on a Port Modify event.

        The event notifies that an interface's link was changed to 'down'.
        """
        interface = event.content['interface']
        if interface.link:
            interface.link.active = False
        self.notify_topology_update()

    @listen_to('.*.interface.is.nni')
    def add_links(self, event):
        """Update the topology with links related to the NNI interfaces."""
        interface_a = event.content['interface_a']
        interface_b = event.content['interface_b']

        link = self._get_link_or_create(interface_a, interface_b)
        interface_a.update_link(link)
        interface_b.update_link(link)

        interface_a.nni = True
        interface_b.nni = True

        self.notify_topology_update()

    # def add_host(self, event):
    #    """Update the topology with a new Host."""

    #    interface = event.content['port']
    #    mac = event.content['reachable_mac']

    #    host = Host(mac)
    #    link = self.topology.get_link(interface.id)
    #    if link is not None:
    #        return

    #    self.topology.add_link(interface.id, host.id)
    #    self.topology.add_device(host)

    #    if settings.DISPLAY_FULL_DUPLEX_LINKS:
    #        self.topology.add_link(host.id, interface.id)

    def notify_topology_update(self):
        """Send an event to notify about updates on the topology."""
        name = 'kytos/topology.updated'
        event = KytosEvent(name=name, content=self._get_topology_dict())
        self.controller.buffers.app.put(event)
