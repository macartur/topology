"""Exceptions raised by this NApp."""

class DeviceException(Exception):
    """Device related exception."""

    def __init__(self, device=None):
        """Take the parameter to inform the user about the error.

        Args:
            device (str, :class:`Device`): The device that was looked for.

        """
        super().__init__()
        self.device = device


class DeviceNotFound(DeviceException):
    """Exception raised when trying to access a device that does not exist."""

    def __str__(self):
        return f"Device {self.device} not found. " + super().__str__()


class PortException(Exception):
    """Port related exceptions."""

    def __init__(self, port=None):
        """Take the parameter to inform the user about the error.

        Args:
            port (str, :class:`Port`): The port that was looked for.

        """
        super().__init__()
        self.port = port


class PortNotFound(PortException):
    """Exception raised when trying to access a port that does not exist."""

    def __str__(self):
        return f"Port {self.port} not found. " + super().__str__()


class InterfaceException(Exception):
    """Interface related exceptions."""

    def __init__(self, interface=None):
        """Take the parameter to inform the user about the error.

        Args:
            interface (str, :class:`Interface`): The Interface that was looked
                for.

        """
        super().__init__()
        self.interface = interface


class InterfaceDisconnected(InterfaceException):
    """When a forbidden action was performed on a disconnected interface."""

    def __str__(self):
        msg = f"The interface {self.interface} is disconnected."
        return msg + super().__str__()


class InterfaceConnected(InterfaceException):
    """When a forbidden action was performed on a connected interface."""

    def __str__(self):
        msg = f"The interface {self.port} is already connected."
        return  msg + super().__str__()


class LinkException(Exception):
    """Link related exception."""

    def __init__(self, link=None):
        """Take the parameter to inform the user about the error.

        Args:
            link (str, :class:`Link`): The link that was looked for.

        """
        super().__init__()
        self.link = link


class LinkNotFound(Exception):
    """Exception raised when trying to access a link that does not exist."""

    def __str__(self):
        return f"Link {self.link} not found. " + super().__str__()


class TopologyException(Exception):
    """Exception generated while working with the Topology class."""
    pass
