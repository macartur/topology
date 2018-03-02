"""Most relevant classes to be used on the topology."""


__all__ = ('Host',)


class Host:
    def __init__(self, mac):
        self.mac = mac

    @property
    def id(self):
        return self.mac

    def as_dict(self):
        return {'mac': self.mac,
                'type': 'host'}
