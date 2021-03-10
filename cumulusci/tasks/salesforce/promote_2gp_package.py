from typing import List, Dict

from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.core.sfdx import get_default_devhub_username
from cumulusci.core.config.sfdx_org_config import SfdxOrgConfig


class Promote2gpPackageVersion(BaseSalesforceApiTask):
    """Promote a 2GP Package version from a Beta to a Production release.

    The terms "promoted" and "released" are the same in the context of
    a 2GP package. Once "promoted" a package is considered to be "released".
    Hence "promotion" of a package is just an update to the Package2Version.IsReleased
    field.
    """

    task_docs = """Use this command to promote a Second Generation managed package.
    Once promoted, 2GP package can be installed into production orgs."""

    task_options = {
        "version_id": {
            "description": "The 04t Id for the package to be promoted.",
            "required": True,
        },
        "auto-promote": {
            "description": "If unpromoted versions of dependent 2GP packages are found, then they are automatically promoted. Defaults to False.",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        if "version_id" not in self.options:
            raise TaskOptionsError("Task option `version_id` is required.")

        version_id = self.options["version_id"]
        if not isinstance(version_id, str) or not version_id.startswith("04t"):
            raise TaskOptionsError(
                "Task option `version_id` must be a valid SubscriberPackageVersion (04t) Id."
            )

    def _init_task(self):
        # TODO: Refactor into utils
        self.devhub_config = self._init_devhub()
        self.tooling = get_simple_salesforce_connection(
            self.project_config,
            self.devhub_config,
            api_version=self.api_version,
            base_url="tooling",
        )

    def _init_devhub(self):
        # TODO: Refactor into utils as this is used by CreatePackageVersion
        # Determine the devhub username for this project
        try:
            devhub_service = self.project_config.keychain.get_service("devhub")
        except ServiceNotConfigured:
            devhub_username = get_default_devhub_username()
        else:
            devhub_username = devhub_service.username
        return SfdxOrgConfig({"username": devhub_username}, "devhub")

    def _run_task(self):
        dependency_04t_ids = self._get_dependency_04t_ids(self.options["version_id"])

        one_gp_deps = self._filter_1gp_deps(dependency_04t_ids)
        if one_gp_deps:
            self.logger.warn("This package has the following 1GP dependencies:")
            self.logger.warn("")
            for dep in one_gp_deps:
                self.logger.warn(
                    f"    Package Name: {dep['name']:20} ReleaseState: {dep['releaseState']}"
                )

        unpromoted_2gp_dependencies = self._get_unpromoted_2gp_dependencies(
            dependency_04t_ids
        )
        if unpromoted_2gp_dependencies and self.options.get("auto_promote", False):
            for dep in unpromoted_2gp_dependencies:
                self._promote_2gp_package(dep["version_id"])
        elif unpromoted_2gp_dependencies:
            self.logger.error("")
            self.logger.error(
                "This package depends on other packages that have not yet been promoted. "
            )
            self.logger.error(
                "The following packages must be promoted before this one."
            )
            self.logger.error(
                "(Use `--auto-promote True` to automatically promote these dependencies):"
            )
            self.logger.error("")
            for dep in unpromoted_2gp_dependencies:
                self.logger.error(f"   Package Name: {dep['name']}")
                self.logger.error(f"   SubscriberPackageVersionId: {dep['version_id']}")
                self.logger.error("")
            return

        self._promote_2gp_package(self.options["version_id"])

    def _get_dependency_04t_ids(self, spv_id: str) -> List[str]:
        """
        @param spv_id: SubscriberPackageVersionId to fetch dependencies for
        @return: list of SubscriberPackageVersionIds (04t) of dependency packages
        """
        subscriber_package_version = self._query_SubscriberPackageVersion(spv_id)

        dependencies = subscriber_package_version["Dependencies"] or {"ids": []}
        dependencies = [d["subscriberPackageVersionId"] for d in dependencies["ids"]]
        return dependencies

    def _filter_1gp_deps(self, spv_ids: List[str]):
        """
        @param dependency_ids: list of SubscriberPackageVersionIds (04t) to filter against
        @return: list of dicts that correspond to 1GP dependency packages. Each dict
        has the keys: "name" and "releaseState".
        """
        # Any 04t without a Package2Version is a 1GP package
        one_gp_04t_ids = [
            spv_id for spv_id in spv_ids if not self._query_Package2Version(spv_id)
        ]
        dep_info = []
        for dep_id in one_gp_04t_ids:
            dep_name = self._get_package_name(dep_id)
            release_state = self._query_SubscriberPackageVersion(dep_id)["ReleaseState"]
            dep_info.append({"name": dep_name, "releaseState": release_state})

        return dep_info

    def _get_package_name(self, spv_id: str):
        """
        @param spv_id: the SubscriberPackageVersionId to find the corresponding name for.
        @returns: str of the package's name
        """
        subscriber_package = self._query_SubscriberPackageVersion(spv_id)
        sp_id = subscriber_package["SubscriberPackageId"]
        subscriber_package = self._query_tooling(
            ["Id", "Name"],
            "SubscriberPackage",
            f"Id='{sp_id}'",
            return_one=True,
            raise_error=True,
        )

        return subscriber_package["Name"]

    def _get_unpromoted_2gp_dependencies(
        self, spv_ids: List[str]
    ) -> List[Dict[str, str]]:
        """
        @param spv_ids: list of SubscriberPackageVersionIds (04t) to check
        @return: a list of 2GP dependency packages. Each dependency is a dict
        with keys: 'name' and 'version_id'.
        """
        unpromoted = []
        for spv_id in spv_ids:
            promoted = self._is_package_version_promoted(spv_id)
            if promoted is None:  # 1GP dependency
                continue
            elif not promoted:
                unpromoted.append(spv_id)

        dep_info = []
        for dep_id in unpromoted:
            dep_name = self._get_package_name(dep_id)
            dep_info.append({"name": dep_name, "version_id": dep_id})

        return dep_info

    def _is_package_version_promoted(self, spv_id: str) -> bool:
        """
        @param: spv_id: the SubscriberPackageVersionId to check
        @return: returns the value for Package2Version.IsReleased if found, None otherwise.
        """
        package2_version = self._query_Package2Version(spv_id)
        if not package2_version:  # This is a 1GP dependency
            return None
        return package2_version["IsReleased"]

    def _promote_2gp_package(self, spv_id: str) -> None:
        """
        @param spv_id: the SubscriberPackageVersionId to promote
        @return: None
        """
        package2_version_id = self._query_Package2Version(spv_id, raise_error=True)[
            "Id"
        ]

        self.logger.info("")
        self.logger.info(f"Promoting package: {self._get_package_name(spv_id)}")
        Package2Version = self._get_tooling_object("Package2Version")
        Package2Version.update(package2_version_id, {"IsReleased": True})
        self.logger.info("Package promoted!")

    def _query_Package2Version(self, spv_id: str, raise_error: bool = False) -> dict:
        """Queries for a Package2Version record with the given SubscriberPackageVersionId"""
        return self._query_tooling(
            ["Id", "IsReleased"],
            "Package2Version",
            f"SubscriberPackageVersionId='{spv_id}'",
            return_one=True,
            raise_error=raise_error,
        )

    def _query_SubscriberPackageVersion(self, id: str) -> dict:
        """Queries for a SubscriberPackageVersion record with the given Id"""
        return self._query_tooling(
            ["Id", "Dependencies", "ReleaseState", "SubscriberPackageId"],
            "SubscriberPackageVersion",
            f"Id='{id}'",
            return_one=True,
            raise_error=True,
        )

    def _query_tooling(
        self,
        fields: List[str],
        obj_name: str,
        where_clause: str,
        return_one: bool = False,
        raise_error: bool = False,
    ) -> Dict[str, str]:
        """
        Queires the Tooling API

        @param fields: list of fields to query for
        @param obj_name: name of the tooling API sObject you want to query
        @param where_clause: the where clause for the query (everything _after_ 'WHERE')
        @param return_one: If true, returns a single sObject record
        @param raise_error: If True, raises an error if no records are found

        @return: None if no records are found, single sObject if `return_one` is True,
        or a list of sObject records if `return_one` is False.
        """
        query = f"SELECT {', '.join(fields)} FROM {obj_name} WHERE {where_clause}"
        res = self.tooling.query(query)

        if not res["records"]:
            if raise_error:
                raise CumulusCIException(f"No records returned for query: {query}")
            return None

        if return_one:
            return res["records"][0]

        return res["records"]
