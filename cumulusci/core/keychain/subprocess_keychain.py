import typing as T

from cumulusci.core.exceptions import ServiceNotConfigured


class SubprocessKeychain(T.NamedTuple):
    """A pretend, in-memory keychain that knows about connected apps and nothing else.

    This keychain is used by Snowfakery to make the connected app available to
    tasks that are running in sub-processes. If Snowfakery ever needs a broader
    range of services thaan just the connected app, this keychain will need to
    become more complex.
    """

    connected_app: T.Any = None

    def get_service(self, name, alias=None):
        if name == "connected_app" and self.connected_app:
            return self.connected_app

        raise ServiceNotConfigured(name)

    def set_org(self, *args):
        pass
