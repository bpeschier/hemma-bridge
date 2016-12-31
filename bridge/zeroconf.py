import socket

import zeroconf


class HemmaService(zeroconf.ServiceInfo):
    def __init__(self, name, port, domain, stype=None, properties=None):
        stype = stype or '_hemma._tcp.'
        properties = properties or {}

        # XXX seems like zeroconf does not work with 0.0.0.0...
        # I think it is because it advertises where to connect to, so we need to
        # figure out what to advertise.
        address = next(filter(
            lambda a: a != '127.0.0.1',
            zeroconf.get_all_addresses(socket.AF_INET))
        )

        full_type = '{}{}'.format(stype, domain)
        full_name = '{}.{}'.format(name, full_type)

        super().__init__(
            full_type,
            full_name,
            port=port,
            properties=properties,
            address=socket.inet_aton(address)
        )
