from cumulusci.salesforce_api.metadata import ApiRetrievePackaged
from cumulusci.tasks.salesforce import BaseRetrieveMetadata
from cumulusci.utils import zip_subfolder


retrieve_packaged_options = BaseRetrieveMetadata.task_options.copy()
retrieve_packaged_options.update(
    {
        "package": {
            "description": "The package name to retrieve.  Defaults to project__package__name",
            "required": True,
        },
        "api_version": {
            "description": (
                "Override the default api version for the retrieve."
                + " Defaults to project__package__api_version"
            )
        },
    }
)


class RetrievePackaged(BaseRetrieveMetadata):
    api_class = ApiRetrievePackaged

    task_options = retrieve_packaged_options

    def _init_options(self, kwargs):
        super(RetrievePackaged, self)._init_options(kwargs)
        if "package" not in self.options:
            self.options["package"] = self.project_config.project__package__name

    def _get_api(self):
        return self.api_class(
            self, self.options["package"], self.options.get("api_version")
        )

    def _extract_zip(self, src_zip):
        src_zip = zip_subfolder(src_zip, self.options.get("package"))
        super(RetrievePackaged, self)._extract_zip(src_zip)
