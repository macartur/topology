"""Most relevant classes to be used on the topology."""
from enum import Enum, IntEnum, unique
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

class Topology:
    """Represents the network topology."""

    _links = set()
    _devices = {}

    def __init__(self):
        """Init a topology object."""
        self._links = set()
        self._devices = {}

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

    @property
    def devices(self):
        """Return all current devices."""
        return list(self._devices.values())

    @property
    def links(self):
        """Return all current links."""
        return list(self._links)

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

    def to_json(self):
        """Export the current topology as a serializeable dict."""
        output = {'devices': {}, 'links': []}
        for device in self.devices:
            output['devices'][device.id] = device.as_dict()

        for link in self._links:
            output['links'].append({'a': link[0],
                                    'b': link[1]})

        try:
            if settings.CUSTOM_LINKS_PATH:
                with open(settings.CUSTOM_LINKS_PATH, 'r') as fp:
                    output['circuits'] = json.load(fp)
        except FileNotFoundError as e:
            pass

        return json.dumps(output)

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
