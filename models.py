"""Most relevant classes to be used on the topology."""
from collections import namedtuple
from copy import copy
from enum import Enum, IntEnum, unique
from pathlib import Path
import json

from napps.kytos.topology import settings
from napps.kytos.topology.exceptions import (DeviceException, DeviceNotFound,
                                             InterfaceConnected,
                                             InterfaceDisconnected,
                                             InterfaceException,
                                             LinkException, PortException,
                                             PortNotFound, TopologyException)

__all__ = ('Device', 'DeviceType', 'Interface', 'Port', 'PortState',
           'Topology')


class Host:
    def __init__(self, mac):
        self.mac = mac

    @property
    def id(self):
        return self.mac

    def as_dict(self):
        return {'mac': self.mac,
                'type': 'host'}


Circuit = namedtuple('Circuit', ['name', 'hops', 'custom_properties',
                                 'hops_ws'])


class Topology:
    """Represents the network topology."""

    _links = set()
    _devices = {}

    def __init__(self):
        """Init a topology object."""
        self._links = set()
        self._devices = {}
        self._get_custom_circuits()
        self._get_custom_property_dpids()

    def _get_custom_property_dpids(self):
        if hasattr(settings, 'CUSTOM_PROPERTY_DPIDS'):
            self._custom_properties = settings.CUSTOM_PROPERTY_DPIDS
        else:
            self._custom_properties = {}

    def _get_custom_circuits(self):
        """Populate the circuits with the correct properties.

        Data will be based on an existing configuration file and a default
        values dictionary in settings.py.
        """
        self._circuits = {}
        if not hasattr(settings, 'CUSTOM_CIRCUITS_PATH'):
            return

        path = Path(settings.CUSTOM_CIRCUITS_PATH)
        if not path.exists():
            return

        with path.open() as custom_file:
            circuits = json.loads(custom_file.read())
        for c in circuits:
            circuit = Circuit(c['name'], c['hops'], c['custom_properties'], [])
            self._circuits[c['name']] = circuit

        for c in self._circuits.values():
            self._circuits[c.name] = Circuit(c.name, c.hops,
                                             c.custom_properties,
                                             self._remove_switch_hops(c.hops))

        # Default for properties
        if hasattr(settings, 'CUSTOM_PROPERTY_DEFAULTS'):
            defaults = settings.CUSTOM_PROPERTY_DEFAULTS
        else:
            defaults = {}

        # Given properties
        all_properties = set([prop for circuit in self._circuits.values() for
                              prop in circuit.custom_properties])
        # Merge properties
        for prop in all_properties:
            if prop not in defaults:
                defaults[prop] = 0

        # Updating properties for simple circuits
        for circuit in self._circuits.values():
            if len(circuit.hops_ws) <= 2:
                new_props = copy(defaults)
                new_props.update(circuit.custom_properties)
                self._circuits[circuit.name] = Circuit(circuit.name,
                                                       circuit.hops,
                                                       new_props,
                                                       circuit.hops_ws)

        # Updating properties for complex circuits
        for circuit in self._circuits.values():
            if len(circuit.hops_ws) > 2:
                to_calculate = [p for p in defaults if p not in
                                circuit.custom_properties]
                for p in to_calculate:
                    p_value = 0
                    for idx, hop in enumerate(circuit.hops_ws):
                        if idx < len(circuit.hops_ws) - 1:
                            next_hop = circuit.hops_ws[idx+1]
                            value = self._get_hop_custom_prop(hop, next_hop, p)
                            p_value += defaults[p] if value is None else value
                    circuit.custom_properties[p] = p_value

    def _get_simple_circuit(self, hopA, hopB):
        """Return a simple circuit with the two specified hosts."""
        for circuit in self._circuits.values():
            if circuit.hops_ws == [hopA, hopB]:
                return circuit
        return None

    def _get_hop_custom_prop(self, hopA, hopB, prop):
        """Return the correct value for a custom property of a simple link."""
        if hopA.split(':')[0:8] == hopB.split(':')[0:8]:
            return 0
        circuit = self._get_simple_circuit(hopA, hopB)
        if circuit is not None:
            return circuit.custom_properties[prop]
        else:
            return None

    def _replace_by_objects(self, interface):
        """Replace interface device and port ids by objects.

        Args:
            interface (Interface): One Interface instance.

        Returns:
            The interface object with it's attributes (device and port)
            containing instances of Device and Port instead of its IDs.

        Raises:
            DeviceException if interface.device is not known by the topology.
            PortNotFound if the device does not have such Port.

        """
        device = self.get_device(interface.device)
        if device is None:
            raise DeviceNotFound(interface.device)

        port = device.get_port(interface.port)
        if port is None:
            raise PortNotFound(interface.port)

        return Interface(device, port)

    def _unset_link_for_interface(self, interface):
        """Unset the link for the given interface."""
        link = self.get_link(interface)
        if link:
            self.unset_link(link)

    def remove_interface_links(self, interface_id):
        links = list(self._links)
        for link in links:
            if interface_id in link:
                self._links.discard(link)

    def add_device(self, new_device):
        """Add a device to the topology known devices.

        Args:
            device (Device): One Device instance.

        """
        self._devices[new_device.id] = new_device

    def remove_device(self, device):
        """Remove a device from the topology known devices.

        Args:
            device (Device): One Device instance.

        """
        try:
            for interface in device.interfaces:
                self.remove_interface_links(interface)

            del self._devices[device.id]

        except KeyError:
            return False

    @property
    def devices(self):
        """Return all current devices."""
        return list(self._devices.values())

    @property
    def links(self):
        """Return all current links."""
        return list(self._links)

    @property
    def circuits(self):
        """Return all current circuits."""
        return [{"name": c.name, "hops": c.hops,
                 "custom_properties": c.custom_properties} for c in
                self._circuits.values()]

    @devices.setter
    def devices(self, value):
        """Overriding devices attribute to avoid direct usage."""
        msg = f'To add or change devices use the proper methods. {value}'
        raise TopologyException(msg)

    @links.setter
    def links(self, value):
        """Overriding links attribute to avoid direct usage."""
        msg = f'To add or change links use the proper methods. {value}'
        raise TopologyException(msg)

    def get_device(self, device):
        """Get the device by the device id.

        Args:
            device (str, Device): Either the Device instance or its id.

        Returns:
            The device instance if it exists
            None else

        """
        try:
            if isinstance(device, Device):
                return self._devices[device.id_]
            return self._devices[device]
        except KeyError:
            return None

    def get_link(self, interface):
        """Return the link for the given interface if it exist else None."""
        for link in self._links:
            if interface in link:
                return link
        return None

    def set_link(self, interface_one, interface_two, properties=None,
                 force=False):
        """Set a new link on the topology."""
        interface_one = self._replace_by_objects(interface_one)
        interface_two = self._replace_by_objects(interface_two)

        if force:
            self._unset_link_for_interface(interface_one)
            self._unset_link_for_interface(interface_two)

        link = Link(interface_one, interface_two, properties)

        self._links[link.id_] = link
        return link

    def add_link(self, endpoint_a, endpoint_b):
        # TODO: Check if the interface has a previous link
        self._links.add((endpoint_a, endpoint_b))

    def preload_topology(self, topology):
        """Preload a topology.

        This will replace the current topology with the given devices and
        links.

        If any error is found on the passed devices or links, then we will just
        abort the operation and restate the topology as it was before this
        method was called.

        Args:
            topology (str, dict): dict/json output on the format of
            Topology.to_json().

        Raises:
            TopologyException if any error was found.

        """
        # first we will save the current devices and links.
        try:
            obj = Topology.from_json(topology)
        except (PortException, DeviceException, InterfaceException,
                LinkException) as exception:
            raise TopologyException(exception)

        self._links = {link.id_: link for link in obj.links}
        self._devices = {device.id_: device for device in obj.devices}

    def to_dict(self):
        """Export the current topology as a serializeable dict."""
        output = {'devices': {}, 'links': []}
        for device in self.devices:
            output['devices'][device.id] = device.as_dict()
            try:
                custom = self._custom_properties[device.id]
            except KeyError:
                custom = {}

            output['devices'][device.id]['custom_properties'] = custom

        for link in self._links:
            output['links'].append({'a': link[0],
                                    'b': link[1]})

        output['circuits'] = self.circuits

        return output

    def to_json(self):
        """Export the current topology as json."""
        return json.dumps(self.to_dict())

    def _remove_switch_hops(self, hops):
        """Remove hops representing a switch in a circuit."""
        output = []
        for hop in hops:
            if len(hop.split(':')) != 8:
                output.append(hop)
        return output

    def _recreate_interface(self, data):
        """Recreate and return an interface.

        Args:
            data (str, dict): dict/json output on the form of
                interface.to_json() method.

        Returns:
            Interface instance.

        """
        device = self.get_device(data['device_id'])
        port = device.get_port(data['port_id'])
        interface = Interface(device, port)
        if data['connected']:
            interface.connect()
            if data['uni']:
                interface.set_as_uni()
            if data['nni']:
                interface.set_as_nni()
        return interface

    @classmethod
    def from_json(cls, json_data):
        """Return a Topology instance based on a dict/json(str)."""
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        obj = cls()

        devices = json_data['devices']
        for device in devices:
            obj.add_device(Device.from_json(device))

        links = json_data['links']
        for link in links:
            # Creating interface one
            data_a = link['interface_one']
            device = obj.get_device(data_a['device_id'])
            interface_one = device.get_interface_for_port(data_a['port_id'])

            # Creating interface two
            data_b = link['interface_two']
            device = obj.get_device(data_b['device_id'])
            interface_two = device.get_interface_for_port(data_b['port_id'])

            obj.set_link(interface_one, interface_two, link['properties'])

            # Updating interface one UNI/NNI status
            if data_a['nni']:
                interface_one.set_as_nni()
            elif data_a['uni']:
                interface_one.set_as_uni()

            # Updating interface two UNI/NNI status
            if data_b['nni']:
                interface_two.set_as_nni()
            elif data_b['uni']:
                interface_two.set_as_uni()

        return obj
