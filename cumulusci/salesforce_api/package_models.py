import logging
from typing import Optional


from cumulusci.core.enums import StrEnum
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_bool_arg
from cumulusci.utils.yaml.model_parser import CCIModel

logger = logging.getLogger(__name__)


class SecurityType(StrEnum):
    """Enum used to specify the component permissioning mode for a package install.

    The values specified by the Tooling API are confusing, and PUSH is not documented.
    We rename here for a little bit of clarity."""

    FULL = "FULL"  # All profiles
    CUSTOM = "CUSTOM"  # Custom profiles
    ADMIN = "NONE"  # System Administrator only
    PUSH = "PUSH"  # No profiles


class NameConflictResolution(StrEnum):
    """Enum used to specify how name conflicts will be resolved when installing an Unlocked Package."""

    BLOCK = "Block"
    RENAME = "RenameMetadata"


# Unlocked Packages only. Default appears to be all but is not documented.
class ApexCompileType(StrEnum):
    ALL = "all"
    PACKAGE = "package"


# Unlocked Packages only. Default is mixed.
class UpgradeType(StrEnum):
    DELETE_ONLY = "delete-only"
    DEPRECATE_ONLY = "deprecate-only"
    MIXED = "mixed"


class PackageInstallOptions(CCIModel):
    """Options governing installation behavior for a managed or unlocked package."""

    activate_remote_site_settings: bool = True
    name_conflict_resolution: NameConflictResolution = NameConflictResolution.BLOCK
    password: Optional[str] = None
    security_type: SecurityType = SecurityType.FULL
    apex_compile_type: Optional[ApexCompileType] = None
    upgrade_type: Optional[UpgradeType] = None

    @staticmethod
    def from_task_options(task_options: dict) -> "PackageInstallOptions":
        options = PackageInstallOptions()  # all parameters are defaulted

        try:
            if "security_type" in task_options:
                options.security_type = SecurityType(task_options["security_type"])
            if "activate_remote_site_settings" in task_options:
                options.activate_remote_site_settings = process_bool_arg(
                    task_options["activate_remote_site_settings"]
                )
            if "name_conflict_resolution" in task_options:
                options.name_conflict_resolution = NameConflictResolution(
                    task_options["name_conflict_resolution"]
                )
            if "password" in task_options:
                options.password = task_options["password"]
            if "apex_compile_type" in task_options:
                options.apex_compile_type = ApexCompileType(
                    task_options["apex_compile_type"]
                )
            if "upgrade_type" in task_options:
                options.upgrade_type = UpgradeType(task_options["upgrade_type"])
        except ValueError as e:
            raise TaskOptionsError(f"Invalid task options: {e}")

        return options


PackageInstallOptions.update_forward_refs()
