import typing as T
from contextlib import nullcontext

from cumulusci.core.exceptions import OrgNotFound, ServiceNotConfigured


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

    # Orgs aren't saved from sub-processes, so the org file isn't locked or re-read.
    # A refresh token rotated in a sub-process isn't saved either.
    def org_lock(self, *args):
        return nullcontext()

    def reload_org(self, name):
        raise OrgNotFound(name)
