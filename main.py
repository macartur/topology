"""Main module of kytos/topology Kytos Network Application.

Manage the network topology
"""
from flask import jsonify, request
from kytos.core import KytosEvent, KytosNApp, log, rest
from kytos.core.helpers import listen_to
from kytos.core.link import Link

# from napps.kytos.topology import settings


class Main(KytosNApp):
    """Main class of kytos/topology NApp.

    This class is the entry point for this napp.
    """

    def setup(self):
        """Initialize the NApp's links list."""
        self.links = {}

    def execute(self):
        """Do nothing."""
        pass

    def shutdown(self):
        """Do nothing."""
        log.info('NApp kytos/topology shutting down.')

    def _get_link_or_create(self, endpoint_a, endpoint_b):
        new_link = Link(endpoint_a, endpoint_b)

        for link in self.links.values():
            if new_link == link:
                return link

        self.links[new_link.id] = new_link
        return new_link

    def _get_switches_dict(self):
        """Return a dictionary with the known switches."""
        return {'switches': {d.id: d.as_dict() for d in
                             self.controller.switches.values()}}

    def _get_topology_dict(self):
        """Return a dictionary with the known topology."""
        return {'topology': {**self._get_switches_dict(),
                             "links": self.links}}

    @rest('v3/')
    def get_topology(self):
        """Return the latest known topology.

        This topology is updated when there are network events.
        """
        return jsonify(self._get_topology_dict())

    # Switch related methods
    @rest('v3/switches')
    def get_switches(self):
        """Return a json with all the switches in the topology."""
        return jsonify(self._get_switches_dict())

    @rest('v3/switches/<dpid>/enable', methods=['POST'])
    def enable_switch(self, dpid):
        """Administratively enable a switch in the topology."""
        try:
            self.controller.switches[dpid].enable()
            return jsonify("Operation successful"), 201
        except KeyError:
            return jsonify("Switch not found"), 404

    @rest('v3/switches/<dpid>/disable', methods=['POST'])
    def disable_switch(self, dpid):
        """Administratively disable a switch in the topology."""
        try:
            self.controller.switches[dpid].disable()
            return jsonify("Operation successful"), 201
        except KeyError:
            return jsonify("Switch not found"), 404

    @rest('v3/switches/<dpid>/metadata')
    def get_switch_metadata(self, dpid):
        """Get metadata from a switch."""
        try:
            return jsonify({"metadata":
                            self.controller.switches[dpid].metadata}), 200
        except KeyError:
            return jsonify("Switch not found"), 404

    @rest('v3/switches/<dpid>/metadata', methods=['POST'])
    def add_switch_metadata(self, dpid):
        """Add metadata to a switch."""
        metadata = request.get_json()
        try:
            self.controller.switches[dpid].extend_metadata(metadata)
            return jsonify("Operation successful"), 201
        except KeyError:
            return jsonify("Switch not found"), 404

    @rest('v3/switches/<dpid>/metadata/<key>', methods=['DELETE'])
    def delete_switch_metadata(self, dpid, key):
        """Delete metadata from a switch."""
        try:
            status = self.controller.switches[dpid].remove_metadata(key)
        except KeyError:
            return jsonify("Switch not found"), 404

        if status:
            return jsonify("Operation successful"), 200
        return jsonify("Metadata not found"), 404

    # Interface related methods
    @rest('v3/interfaces')
    def get_interfaces(self):
        """Return a json with all the interfaces in the topology."""
        interfaces = {}
        switches = self._get_switches_dict()
        for switch in switches['switches'].values():
            for interface_id, interface in switch['interfaces'].items():
                interfaces[interface_id] = interface

        return jsonify({'interfaces': interfaces})

    @rest('v3/interfaces/<interface_id>/enable', methods=['POST'])
    def enable_interface(self, interface_id):
        """Administratively enable an interface in the topology."""
        switch_id = ":".join(interface_id.split(":")[:-1])
        interface_number = int(interface_id.split(":")[-1])

        try:
            switch = self.controller.switches[switch_id]
        except KeyError:
            return jsonify("Switch not found"), 404

        try:
            switch.interfaces[interface_number].enable()
        except KeyError:
            return jsonify("Interface not found"), 404

        return jsonify("Operation successful"), 201

    @rest('v3/interfaces/<interface_id>/disable', methods=['POST'])
    def disable_interface(self, interface_id):
        """Administratively disable an interface in the topology."""
        switch_id = ":".join(interface_id.split(":")[:-1])
        interface_number = int(interface_id.split(":")[-1])

        try:
            switch = self.controller.switches[switch_id]
        except KeyError:
            return jsonify("Switch not found"), 404

        try:
            switch.interfaces[interface_number].disable()
        except KeyError:
            return jsonify("Interface not found"), 404

        return jsonify("Operation successful"), 201

    @rest('v3/interfaces/<interface_id>/metadata')
    def get_interface_metadata(self, interface_id):
        """Get metadata from an interface."""
        switch_id = ":".join(interface_id.split(":")[:-1])
        interface_number = int(interface_id.split(":")[-1])
        try:
            switch = self.controller.switches[switch_id]
        except KeyError:
            return jsonify("Switch not found"), 404

        try:
            interface = switch.interfaces[interface_number]
        except KeyError:
            return jsonify("Interface not found"), 404

        return jsonify({"metadata": interface.metadata}), 200

    @rest('v3/interfaces/<interface_id>/metadata', methods=['POST'])
    def add_interface_metadata(self, interface_id):
        """Add metadata to an interface."""
        metadata = request.get_json()

        switch_id = ":".join(interface_id.split(":")[:-1])
        interface_number = int(interface_id.split(":")[-1])
        try:
            switch = self.controller.switches[switch_id]
        except KeyError:
            return jsonify("Switch not found"), 404

        try:
            interface = switch.interfaces[interface_number]
        except KeyError:
            return jsonify("Interface not found"), 404

        interface.extend_metadata(metadata)
        return jsonify("Operation successful"), 201

    @rest('v3/interfaces/<interface_id>/metadata/<key>', methods=['DELETE'])
    def delete_interface_metadata(self, interface_id, key):
        """Delete metadata from an interface."""
        switch_id = ":".join(interface_id.split(":")[:-1])
        interface_number = int(interface_id.split(":")[-1])
        try:
            switch = self.controller.switches[switch_id]
        except KeyError:
            return jsonify("Switch not found"), 404

        try:
            interface = switch.interfaces[interface_number]
        except KeyError:
            return jsonify("Interface not found"), 404

        status = interface.remove_metadata(key)
        if status:
            return jsonify("Operation successful"), 200
        return jsonify("Metadata not found"), 404

    # Link related methods
    @rest('v3/links')
    def get_links(self):
        """Return a json with all the links in the topology.

        Links are connections between interfaces.
        """
        return jsonify({"links": {link.id: link.as_dict() for link in
                                  self.links.values()}}), 200

    @rest('v3/links/<link_id>/enable', methods=['POST'])
    def enable_link(self, link_id):
        """Administratively enable a link in the topology."""
        try:
            self.links[link_id].enable()
        except KeyError:
            return jsonify("Link not found"), 404

        return jsonify("Operation successful"), 201

    @rest('v3/links/<link_id>/disable', methods=['POST'])
    def disable_link(self, link_id):
        """Administratively disable a link in the topology."""
        try:
            self.links[link_id].disable()
        except KeyError:
            return jsonify("Link not found"), 404

        return jsonify("Operation successful"), 201

    @rest('v3/links/<link_id>/metadata')
    def get_link_metadata(self, link_id):
        """Get metadata from a link."""
        try:
            return jsonify({"metadata": self.links[link_id].metadata}), 200
        except KeyError:
            return jsonify("Link not found"), 404

    @rest('v3/links/<link_id>/metadata', methods=['POST'])
    def add_link_metadata(self, link_id):
        """Add metadata to a link."""
        metadata = request.get_json()
        try:
            self.links[link_id].extend_metadata(metadata)
            return jsonify("Operation successful"), 201
        except KeyError:
            return jsonify("Link not found"), 404

    @rest('v3/links/<link_id>/metadata/<key>', methods=['DELETE'])
    def delete_link_metadata(self, link_id, key):
        """Delete metadata from a link."""
        try:
            status = self.links[link_id].remove_metadata(key)
        except KeyError:
            return jsonify("Link not found"), 404

        if status:
            return jsonify("Operation successful"), 200
        return jsonify("Metadata not found"), 404

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
