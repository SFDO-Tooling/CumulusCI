from cumulusci.tasks.salesforce import Deploy
from cumulusci.salesforce_api.package_zip import CreatePackageZipBuilder


class CreatePackage(Deploy):
    task_options = {
        "package": {
            "description": "The name of the package to create.  Defaults to project__package__name",
            "required": True,
        },
        "api_version": {
            "description": "The api version to use when creating the package.  Defaults to project__package__api_version",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super(CreatePackage, self)._init_options(kwargs)
        if "package" not in self.options:
            self.options["package"] = self.project_config.project__package__name
        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version

    def _get_package_zip(self, path=None):
        return CreatePackageZipBuilder(
            self.options["package"], self.options["api_version"]
        )()
