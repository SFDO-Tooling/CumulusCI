from typing import Dict, List, Optional

from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.config.util import get_devhub_config
from cumulusci.core.dependencies.dependencies import PackageVersionIdDependency
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.core.github import get_version_id_from_tag
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.tasks.create_package_version import PackageVersionNumber
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class PromotePackageVersion(BaseSalesforceApiTask):
    """
    Promote a 2GP Package version from a Beta to a Production release.

    The terms "promoted" and "released" are the same in the context of
    a 2GP package. Once "promoted" a package is considered to be "released".
    Hence, the "promotion" of a package is just an update to the
    Package2Version.IsReleased field.

    The abbreviation `spv` in variable names is shorthand for "SubscriberPackageVersion".
    """

    task_docs = """Promote a Second Generation package (managed or unlocked).
    Lists any 1GP dependencies that are detected, as well as
    any dependency packages that have not been promoted.
    Once promoted, the 2GP package can be installed into production orgs."""

    task_options = {
        "version_id": {
            "description": "The SubscriberPackageVersion (04t) Id for the target package.",
            "required": False,
        },
        "promote_dependencies": {
            "description": (
                "Automatically promote any unpromoted versions of dependency 2GP packages that are detected."
            ),
            "required": False,
        },
    }

    # We do use a Salesforce org, but it's the dev hub obtained using get_devhub_config,
    # so the user does not need to specify an org on the CLI
    salesforce_task = False

    # Since self.org_config is unused, don't try to refresh its token
    def _update_credentials(self):
        pass

    def _init_options(self, kwargs) -> None:
        super()._init_options(kwargs)

        version_id = self.options.get("version_id")
        if version_id and (
            not isinstance(version_id, str) or not version_id.startswith("04t")
        ):
            raise TaskOptionsError(
                "Task option `version_id` must be a valid SubscriberPackageVersion (04t) Id"
            )

    def _init_task(self) -> None:
        self.tooling = get_simple_salesforce_connection(
            self.project_config,
            get_devhub_config(self.project_config),
            api_version=self.api_version,
            base_url="tooling",
        )

    def _run_task(self) -> None:
        """Orchestrate the task"""
        version_id = self.options.get("version_id")
        if not version_id:
            version_id = self._resolve_version_id()

        dependencies = self._get_dependency_info(version_id)

        self._process_one_gp_deps(dependencies)
        should_exit = self._process_two_gp_deps(dependencies)

        if should_exit:
            return

        target_package_info = self._get_target_package_info(version_id)
        self._promote_package_version(target_package_info)
        self.return_values = {
            "dependencies": [
                PackageVersionIdDependency(version_id=d["version_id"])
                for d in dependencies
            ],
            "version_id": version_id,
            "version_number": target_package_info["package_version_number"],
        }

    def _resolve_version_id(self) -> str:
        """
        If a SubscriberPackageVersionId has not been specified we need to
        auto-resolve a version_id from the tag on our current commit

        @returns: (str) the SubscriberPackageVersionId from the current repo commit
        """
        self.logger.info(
            "No version_id specified. Automatically resolving to latest available Beta version."
        )
        tag_name = self.project_config.get_latest_tag(beta=True)
        repo = self.project_config.get_repo()
        version_id = get_version_id_from_tag(repo, tag_name)
        self.logger.info(f"Resolved to version: {version_id}")
        self.logger.info("")
        return version_id

    def _get_dependency_info(self, spv_id: str) -> Optional[List[Dict]]:
        """
        Given a SubscriberPackageVersionId (04t) return a list of
        dictionaries with info on all dependency packages present.

        @param spv_id: a SubscriberPackageVersionId
        @returns: a dict with the following shape:
        {
            "is_2gp": (bool) whether or not this dependency is a 2GP package
            "is_promoted": whether or not this package is already promoted (only present if is_2gp is True)
            "Package2VersionId": The Id from the corresponding Package2Version record
            "name": (str) The name of the package
            "release_state": (str) the package's release state
            "version_id": (str) the SubscriberPackageVersionId (04t) of the dependency
        }
        """
        dependency_spv_ids = self._get_dependency_spv_ids(spv_id)

        dependencies = []
        for spv_id in dependency_spv_ids:
            subscriber_package_version = self._query_SubscriberPackageVersion(spv_id)
            subscriber_package = self._query_SubscriberPackage(
                subscriber_package_version["SubscriberPackageId"]
            )
            package_2_version = self._query_Package2Version(spv_id)

            info = {
                "name": subscriber_package["Name"],
                "release_state": subscriber_package_version["ReleaseState"],
                "version_id": spv_id,
            }
            if package_2_version:
                info["is_2gp"] = True
                info["is_promoted"] = package_2_version["IsReleased"]
                info["Package2VersionId"] = package_2_version["Id"]
            else:
                # It's a 1GP dependency if no Package2Version record is present
                info["is_2gp"] = False
                info["is_promoted"] = None
                info["Package2VersionId"] = None

            dependencies.append(info)

        self.logger.info(f"Total dependencies found: {len(dependencies)}")
        return dependencies

    def _get_dependency_spv_ids(self, spv_id: str) -> List[str]:
        """
        @param spv_id: SubscriberPackageVersionId to fetch dependencies for
        @return: list of SubscriberPackageVersionIds (04t) of dependency packages
        """
        subscriber_package_version = self._query_SubscriberPackageVersion(spv_id)
        dependencies = subscriber_package_version["Dependencies"] or {"ids": []}
        dependencies = [d["subscriberPackageVersionId"] for d in dependencies["ids"]]
        return dependencies

    def _process_one_gp_deps(self, dependencies: List[Dict]) -> None:
        """
        Log any 1GP dependecies that are present.

        @param dependencies: list of dependencies to process
        """
        one_gp_deps = self._filter_one_gp_deps(dependencies)
        if one_gp_deps:
            self.logger.warning("")
            self.logger.warning("This package has the following 1GP dependencies:")
            for dep in one_gp_deps:
                self.logger.warning("")
                self.logger.warning(f"    Package Name: {dep['name']}")
                self.logger.warning(f"    Release State: {dep['release_state']}")

    def _process_two_gp_deps(self, dependencies: List[Dict]) -> bool:
        """
        If we're auto-promoting then auto-promote!
        Otherwise, log which dependencies need promoting.

        @param dependencies: list of dependencies to process
        @return: a should_exit indicator to tell _run_task() whether or not to exit
        """
        two_gp_deps = self._filter_two_gp_deps(dependencies)
        unpromoted_two_gp_deps = self._filter_unpromoted_two_gp_deps(dependencies)

        self.logger.info("")
        self.logger.info(f"Total 2GP dependencies: {len(two_gp_deps)}")
        self.logger.info(f"Unpromoted 2GP dependencies: {len(unpromoted_two_gp_deps)}")

        should_exit = False
        if unpromoted_two_gp_deps and self.options.get("promote_dependencies", False):
            for d in unpromoted_two_gp_deps:
                self._promote_package_version(d)
        elif unpromoted_two_gp_deps:
            # we only want _run_task() to exit if unpromoted
            # 2GP deps are present and we aren't auto-promoting
            should_exit = True
            self.logger.error("")
            self.logger.error(
                "This package depends on other packages that have not yet been promoted."
            )
            self.logger.error(
                "The following packages must be promoted before this one."
            )
            self.logger.error(
                "(Use `--promote_dependencies True` to automatically promote these dependencies):"
            )
            self.logger.error("")
            for dep in unpromoted_two_gp_deps:
                self.logger.error(f"   Package Name: {dep['name']}")
                self.logger.error(f"   SubscriberPackageVersionId: {dep['version_id']}")
                self.logger.error("")

        return should_exit

    def _get_target_package_info(self, spv_id: str) -> Dict:
        """
        @param spv_id: SubscriberPackageVersionId of the target package
        @returns: dict of info on the target package with the following:
        {
            "name": name of the package,
            "Package2VersionId": Id of the corresponding Package2Verison record
        }
        """
        package_2_version = self._query_Package2Version(spv_id)
        version_number = PackageVersionNumber(**package_2_version)

        return {
            "name": self.project_config.project__name,
            "Package2VersionId": package_2_version["Id"],
            "version_id": spv_id,
            "package_version_number": version_number.format(),
        }

    def _promote_package_version(self, package_info: Dict) -> None:
        """
        Promote the 2GP package associated with the given SubscriberPackageVersionId

        @param spv_id: the SubscriberPackageVersionId to promote
        """
        self.logger.info("")
        self.logger.info(
            f"Promoting package: {package_info['name']} ({package_info['version_id']})"
        )

        Package2Version = self._get_tooling_object("Package2Version")
        Package2Version.update(package_info["Package2VersionId"], {"IsReleased": True})

        self.logger.info("Package promoted!")

    def _query_Package2Version(
        self, spv_id: str, raise_error: bool = False
    ) -> Optional[Dict]:
        """Queries for a Package2Version record with the given SubscriberPackageVersionId"""
        try:
            return self._query_one_tooling(
                [
                    "Id",
                    "BuildNumber",
                    "MajorVersion",
                    "MinorVersion",
                    "PatchVersion",
                    "IsReleased",
                ],
                "Package2Version",
                where_clause=f"SubscriberPackageVersionId='{spv_id}'",
                raise_error=raise_error,
            )
        except SalesforceMalformedRequest as e:
            if "Object type 'Package2' is not supported" in e.content[0]["message"]:
                raise TaskOptionsError(
                    "This org does not have a Dev Hub with 2nd-generation packaging enabled. "
                    "Make sure you are using the correct org and/or check the Dev Hub settings in Setup."
                )
            raise  # pragma: no cover

    def _query_SubscriberPackage(self, sp_id: str) -> Optional[Dict]:
        """Queries for a SubscriberPackage with the given SubscriberPackageId"""
        return self._query_one_tooling(
            ["Id", "Name"],
            "SubscriberPackage",
            where_clause=f"Id='{sp_id}'",
            raise_error=True,
        )

    def _query_SubscriberPackageVersion(self, spv_id: str) -> Optional[Dict]:
        """Queries for a SubscriberPackageVersion record with the given SubscriberPackageVersionId"""
        return self._query_one_tooling(
            [
                "Id",
                "Dependencies",
                "ReleaseState",
                "SubscriberPackageId",
            ],
            "SubscriberPackageVersion",
            where_clause=f"Id='{spv_id}'",
            raise_error=True,
        )

    def _query_one_tooling(
        self,
        fields: List[str],
        obj_name: str,
        where_clause: str = None,
        raise_error=False,
    ) -> Optional[Dict]:
        """
        Queries the Tooling API and returns a _single_ sObject (or None).
        See docstring of _query_tooling() for param info.
        """
        records = self._query_tooling(
            fields, obj_name, where_clause=where_clause, raise_error=raise_error
        )
        return records[0] if records else None

    def _query_tooling(
        self,
        fields: List[str],
        obj_name: str,
        where_clause: str = None,
        raise_error: bool = False,
    ) -> Optional[List[Dict]]:
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
        query = f"SELECT {', '.join(fields)} FROM {obj_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        res = self.tooling.query_all(query)

        if not res["records"] or res["totalSize"] == 0:
            if raise_error:
                raise CumulusCIException(f"No records returned for query: {query}")
            return None

        return res["records"]

    def _filter_one_gp_deps(self, dependencies: List[Dict]) -> List[Dict]:
        """Return only 1GP dependencies"""
        return [d for d in dependencies if not d["is_2gp"]]

    def _filter_two_gp_deps(self, dependencies: List[Dict]) -> List[Dict]:
        """Return only 2GP dependencies"""
        return [d for d in dependencies if d["is_2gp"]]

    def _filter_unpromoted_two_gp_deps(self, dependencies: List[Dict]) -> List[Dict]:
        """Return only 2GP dependencies that are not yet promoted"""
        return [d for d in dependencies if d["is_2gp"] and not d["is_promoted"]]
