"""Most relevant classes to be used on the topology."""


__all__ = ('Host', 'Topology')


class Topology:
    """Represent the topology with links and switches."""
    def __init__(self, switches, links):
        self.switches = switches
        self.links = links


class Host:
    def __init__(self, mac):
        self.mac = mac

    @property
    def id(self):
        return self.mac

    def as_dict(self):
        return {'mac': self.mac,
                'type': 'host'}
