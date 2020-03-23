from cumulusci.core.utils import deprecated_import

InstallPackageVersion = deprecated_import(
    "cumulusci.tasks.salesforce.install_package_version.InstallPackageVersion"
)

__all__ = ["InstallPackageVersion"]
