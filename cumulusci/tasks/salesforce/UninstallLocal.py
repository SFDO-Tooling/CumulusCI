from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.tasks.salesforce import BaseUninstallMetadata


class UninstallLocal(BaseUninstallMetadata):
    def _get_destructive_changes(self, path=None):
        if not path:
            path = self.options["path"]

        generator = PackageXmlGenerator(
            directory=path,
            api_version=self.api_version,
            delete=True,
        )
        return generator()
