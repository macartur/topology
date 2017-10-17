"""Most relevant classes to be used on the topology."""
from enum import Enum, IntEnum, unique
import json

from napps.kytos.topology.exceptions import (DeviceException, DeviceNotFound,
                                             InterfaceConnected,
                                             InterfaceDisconnected,
                                             InterfaceException,
                                             LinkException, PortException,
                                             PortNotFound, TopologyException)

__all__ = ('Device', 'DeviceType', 'Interface', 'Port', 'PortState',
           'Topology')


@unique
class DeviceType(Enum):
    """Device types."""

    SWITCH = 0
    HOST = 1


@unique
class PortState(IntEnum):
    """Port states."""

    DOWN = 0
    UP = 1  # pylint: disable=invalid-name


class Port:
    """Represent a port from a Device.

    Each device can hold one or more ports.

    """

    def __init__(self, number=None, mac=None, properties=None,
                 state=PortState.UP):
        """Init the port."""
        if number is None and mac is None:
            raise PortException('You must pass or the number or the mac.')
        #: Port number
        self.number = number
        #: Port mac address
        self.mac = mac
        #: Dict with port properties , such as speed, bandwith, etc.
        self.properties = properties or {}
        #: Port state, one of PortState enum values.
        self.state = state

    @property
    def id_(self):
        """Port ID is based on its MACAddress.

        The ID will be the MAC Address without ':' and no left zeroes.

        Returns:
            Port ID (string).

        """
        return self.number or ''.join(self.mac.split(':')).lstrip('0')

    @classmethod
    def from_json(cls, json_data):
        """Return a Port instance based on a dict/json(str)."""
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        return cls(**json_data)

    @property
    def state(self):
        """State property, accepts one of PortState values."""
        return self._state

    @state.setter
    def state(self, value):
        """Set state checking if it is an instance of PortState enum."""
        if isinstance(value, PortState):
            self._state = value
        elif isinstance(value, int):
            self._state = PortState(value)
        else:
            self._state = PortState[value]

    def to_json(self):
        """Export the current port as a serializeable dict."""
        output = dict(vars(self))
        output['state'] = self.state.value
        del output['_state']
        return output


class Device:
    """Class that represent a 'NODE' in the topology graph.

    A Device can be one of the 'DeviceType' values from DeviceType enum.

    Each device will hold one or more ports.

    A port is how Devices connects between themselves and also each
    port can be connected to only one other device/port.

    """

    def __init__(self, device_id, dtype=DeviceType.SWITCH, ports=None):
        """Instantiate a device."""
        #: Switch or host ID
        self.device_id = device_id
        #: DeviceType
        self.dtype = dtype
        #: list of ports (instances of Port)
        self._ports = {}
        ports = ports or []
        for port in ports:
            self.add_port(port)

    @property
    def id_(self):
        """Return the device_id as the device id."""
        return self.device_id

    @property
    def dtype(self):
        """Return the device type."""
        return self._dtype

    @dtype.setter
    def dtype(self, dtype):
        """Set the device type checking if it is a DeviceType.

        Args:
            dtype (:class:`DeviceType`): One of the existent devices type.

        Raises:
            KeyError if there is no such device type on DeviceType.

        """
        if isinstance(dtype, DeviceType):
            self._dtype = dtype
        elif isinstance(dtype, int):
            self._dtype = DeviceType(dtype)
        else:
            self._dtype = DeviceType[dtype]

    def add_port(self, port):
        """Add a port to the device.

        Args:
            port (:class:`Port`): An instance of Port.

        Raises:
            DeviceException if port is not an instance of Port or if the given
                port was already added to the device.

        """
        if not isinstance(port, Port):
            raise DeviceException('Port must be an instance of Port.')

        if self.has_port(port):
            msg = f'Port {port.id_} already added to the device {self.id_}'
            raise DeviceException(msg)

        self._ports[port.id_] = port

    def remove_port(self, port):
        """Remove a port from current device.

        Args:
            port (Port): The instance of Port to be removed.

        """
        try:
            del self._ports[port.id_]
        except KeyError:
            pass

    def has_port(self, port):
        """Check if the device have the given port.

        Args:
            port (int, str, Port): May be either an instance of Port or an int
                or a string. Both int and str would be the id of the port.

        Returns:
            True if the port was found on the device.
            False otherwise.

        """
        if self.get_port(port):
            return True
        else:
            return False

    def get_port(self, port):
        """Get a Port from the current device.

        Args:
            port (int, str, Port): May be either an instance of Port or an int
                or a string. Both int and str would be the id of the port.

        Returns:
            The registered port instance from the Device if it was found by
                its id.
            None if the por was not found.

        """
        try:
            if isinstance(port, Port):
                return self._ports[port.id_]
            # Assuming that port is the id of a port.
            return self._ports[port]
        except (KeyError, IndexError) as error:
            return None

    @property
    def ports(self):
        """Return the list of current ports."""
        return list(self._ports.values())

    @ports.setter
    def ports(self, ports):
        """Set all ports."""
        if isinstance(ports, dict):
            ports = ports.values
        for port in ports:
            self.add_port(port)

    @property
    def ports_ids(self):
        """Return the list of ports ids."""
        return list(self._ports.keys())

    def to_json(self):
        """Export the current device as a serializeable dict."""
        output = dict(vars(self))
        output['dtype'] = output['_dtype'].value
        del output['_dtype']
        del output['_ports']
        output['ports'] = [port.to_json() for port in self.ports]
        return output

    @classmethod
    def from_json(cls, json_data):
        """Return a Device instance based on a dict/json(str)."""
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        ports_jsons = json_data['ports']
        ports = []
        for port in ports_jsons:
            ports.append(Port.from_json(port))
        json_data['ports'] = ports
        return cls(**json_data)

    def get_interface_for_port(self, port_id):
        """Return an Interface object for the given port_id.

        Args:
            port_id (str): Port id.

        """
        return Interface(self, self.get_port(port_id))


class Interface:
    """Represent an interface on the topology.

    This is the element that can be 'linked' to another on the topology. It is
    composed by a device and a port.

    """

    def __init__(self, device, port):
        """Init the Interface instance."""
        #: instance of Device
        self.device = device
        #: Instance of Port
        self.port = port
        #: Is this an NNI port
        self._nni = False
        #: Is this a UNI port
        self._uni = False
        #: Is this port connected to any other port? True or False
        self._connected = False

    @property
    def id_(self):
        """Return the id of the interface.

        This id is the composition between device id and port id.

        """
        return f'{self.device.id_}:{self.port.id_}'

    def is_connected(self):
        """Check if the device is flagged as connected.

        Returns:
            True if the switch is flagged as connected.
            False if not.

        """
        return self._connected is True

    def connect(self):
        """Flag the switch as connected."""
        self._connected = True

    def disconnect(self):
        """Flag the switch as disconnected.

        It also update the _nni and _uni attributes to False, since we cannot
        have an UNI or a NNI on a disconnected interface.

        """
        self._nni = False
        self._uni = False
        self._connected = False

    def is_nni(self):
        """Is this port a NNI.

        If the port is not connected, then we return False.

        Returns:
            True if it is connected and is flagged as a NNI .
            False if not.

        """
        return self.is_connected() and self._nni

    def is_uni(self):
        """Is this port a UNI.

        If the port is not connected, then we return False.

        Returns:
            True if it is connected and is flagged as an UNI .
            False if not.

        """
        return self.is_connected() and self._uni

    def set_as_nni(self):
        """Set the current port as a NNI port if it is connected."""
        if not self.is_connected():
            msg = 'Disconnected ports cannot be set as NNI.'
            raise InterfaceDisconnected(self.id_, msg)
        self._nni = True
        self._uni = False

    def set_as_uni(self):
        """Set the current port as a UNI port if it is connected.

        Also check if it is not a NNI interface because NNI overcomes UNI.

        """
        if not self.is_connected():
            msg = 'Disconnected ports cannot be set as UNI.'
            raise InterfaceDisconnected(self.id_, msg)

        if self.is_nni():
            raise InterfaceException(self.id_,
                                     'Cannot set a NNI interface as UNI.')
        self._uni = True
        self._nni = False

    def to_json(self):
        """Export the current interface as a serializeable dict.

        ATTENTION: This method will export device and port IDs only, not the
        serialized object. So if you want to recreate this interface you will
        need to create a new Link object passing the device and port correct
        instances.
        """
        output = {
            'device_id': self.device.id_,
            'port_id': self.port.id_,
            'connected': self._connected,
            'uni': self._uni,
            'nni': self._nni
        }
        return output

    @classmethod
    def from_json(cls, json_data):
        """YOU CANNOT RECREATE AN INTERFACE FROM A JSON.

        SINCE AN INTERFACE NEED TO HAVE REFERENCE TO A DEVICE AND A PORT, WE
        WON'T CREATE THESE INSTANCES, YOU NEED TO GET THEM FROM WHEREVER THEY
        ARE (TOPOLOGY MUCH PROBABLY) AND THEN CREATE THE NEW INTERFACE. THE
        OUTPUTTED JSON WILL ONLY HELP YOU BY IDENTIFYING THE DEVICE ID, PORT ID
        AND THE OTHER STATE INFORMATION SUCH AS CONNECTED, UNI AND NNI.

        Raises:
            InterfaceException

        """

        raise InterfaceException(Interface.from_json.__doc__)


class Link:
    """Represents a link between two devices/ports."""

    def __init__(self, interface_one, interface_two, properties=None):
        """Create a Link.

        Args:
            interface_one (Interface): holds Device and Port instances.
            interface_two (Interface): holds Device and Port instances.

        """
        msg = ''
        if interface_one.is_connected():
            msg += f'Interface {interface_one.id_} is already connected; '
        if interface_two.is_connected():
            msg += f'Interface {interface_two.id_} is already connected; '

        if msg:
            msg += 'You must disconnect the interfaces before (re)connecting.'
            raise InterfaceConnected(msg)

        self.interface_one = interface_one
        self.interface_two = interface_two
        self.properties = properties

        self.interface_one.connect()
        self.interface_two.connect()

    @property
    def id_(self):
        """Return the Link ID.

        It is a composition between both interfaces ids joined by a dash.

        """
        return f'{self.interface_one.id_}-{self.interface_two.id_}'

    def unlink(self):
        """Unlink the interfaces."""
        self.interface_one.disconnect()
        self.interface_two.disconnect()
        self.interface_one = None
        self.interface_two = None

    def to_json(self):
        """Export the current link as a serializeable dict."""
        output = {
            'interface_one': self.interface_one.to_json(),
            'interface_two': self.interface_two.to_json(),
            'properties': dict(self.properties)
        }
        return output

    @classmethod
    def from_json(cls, json_data):
        """YOU CANNOT RECREATE A LINK FROM A JSON.

        SINCE A LINK NEED TO HAVE REFERENCE TO TWO INTERFACES, WE
        WON'T CREATE THESE INSTANCES, YOU NEED TO GET THEM FROM WHEREVER THEY
        ARE (TOPOLOGY MUCH PROBABLY) AND THEN CREATE THE NEW LINK. THE
        OUTPUTTED JSON WILL ONLY HELP YOU BY IDENTIFYING THE INTERFACES AND
        THE LINK PROPERTIES.

        Raises:
            LinkException

        """

        raise LinkException(Link.from_json.__doc__)


class Topology:
    """Represents the network topology."""

    _links = {}
    _devices = {}

    def __init__(self):
        """Init a topology object."""
        self._links = {}
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

    def add_device(self, new_device):
        """Add a device to the topology known devices.

        Args:
            device (Device): One Device instance.

        """
        if not isinstance(new_device, Device):
            raise Exception('Device must be an instance of Device.')
        old_device = self.get_device(new_device)
        if old_device is None:
            self._devices[new_device.id_] = new_device

    @property
    def devices(self):
        """Return all current devices."""
        return list(self._devices.items())

    @property
    def links(self):
        """Return all current links."""
        return list(self._links.items())

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
        i_id = interface.id_
        for link in self._links.values():
            if i_id in [link.interface_one.id_, link.interface_two.id_]:
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

    def unset_link(self, link):
        """Unset a link."""
        interface_one = link.interface_one
        interface_two = link.interface_two
        interface_one.disconnect()
        interface_two.disconnect()
        del self._links[link.id_]

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
        output = {'devices': [], 'links': []}
        for device in self.devices:
            output['devices'].append(device.to_json())

        for link in self.links:
            output['links'].append(link.to_json())

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
