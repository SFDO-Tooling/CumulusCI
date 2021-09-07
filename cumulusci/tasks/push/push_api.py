import json
from functools import lru_cache

from simple_salesforce import SalesforceMalformedRequest

from cumulusci.tasks.bulkdata.step import BulkApiQueryOperation


def batch_list(data, batch_size):
    batch_list = []
    batch_data = []
    for item in data:
        batch_data.append(item)
        if len(batch_data) == batch_size:
            batch_list.append(batch_data)
            batch_data = []
    if batch_data:
        batch_list.append(batch_data)
    return batch_list


class BasePushApiObject(object):
    def format_where(self, id_field, where=None):
        base_where = "%s = '%s'" % (id_field, self.sf_id)
        if where:
            where = "%s AND (%s)" % (base_where, where)
        else:
            where = base_where
        return where


# Push API Object Models


class MetadataPackage(BasePushApiObject):
    def __init__(self, push_api, name, sf_id=None, namespace=None):
        self.push_api = push_api
        self.sf_id = sf_id
        self.name = name
        self.namespace = namespace

    def get_package_versions(self, where=None, limit=None):
        where = self.format_where("MetadataPackageId", where)
        return self.push_api.get_package_versions(where, limit)

    def get_package_version_objs(self, where=None, limit=None):
        where = self.format_where("MetadataPackageId", where)
        return self.push_api.get_package_version_objs(where, limit)

    def get_package_versions_by_id(self, where=None, limit=None):
        where = self.format_where("MetadataPackageId", where)
        return self.push_api.get_package_versions_by_id(where, limit)


class MetadataPackageVersion(BasePushApiObject):
    def __init__(
        self, push_api, package, name, state, major, minor, patch, build, sf_id=None
    ):
        self.push_api = push_api
        self.sf_id = sf_id
        self.package = package
        self.name = name
        self.state = state
        self.major = major
        self.minor = minor
        self.patch = patch
        self.build = build

    @property
    def version_number(self):
        parts = [str(self.major), str(self.minor)]
        if self.patch:
            parts.append(str(self.patch))
        version_number = ".".join(parts)
        if self.state == "Beta":
            version_number += " (Beta %s)" % self.build
        return version_number

    def get_newer_released_version_objs(self):
        where = (
            f"MetadataPackageId = '{self.package.sf_id}' AND ReleaseState = 'Released'"
        )
        result = [
            package_version
            for package_version in self.package.get_package_version_objs(where)
            if (package_version.major, package_version.minor, package_version.patch)
            > (
                self.major,
                self.minor,
                self.patch,
            )
        ]
        return result

    def get_older_released_version_objs(self, min_version=None):
        if min_version:
            minimum_version = (min_version.major, min_version.minor, min_version.patch)

        where = f"MetadataPackageId = '{self.package.sf_id}' AND ReleaseState = 'Released'"  # AND "
        if min_version:
            result = [
                package_version
                for package_version in self.package.get_package_version_objs(where)
                if (package_version.major, package_version.minor, package_version.patch)
                < (self.major, self.minor, self.patch)
                and (
                    package_version.major,
                    package_version.minor,
                    package_version.patch,
                )
                >= minimum_version
            ]
        else:
            result = [
                package_version
                for package_version in self.package.get_package_version_objs(where)
                if (package_version.major, package_version.minor, package_version.patch)
                < (self.major, self.minor, self.patch)
            ]
        return result

    def get_subscribers(self, where=None, limit=None):
        where = self.format_where("MetadataPackageVersionId", where)
        return self.push_api.get_subscribers(where, limit)

    def get_subscriber_objs(self, where=None, limit=None):
        where = self.format_where("MetadataPackageVersionId", where)
        return self.push_api.get_subscriber_objs(where, limit)

    def get_subscribers_by_org_key(self, where=None, limit=None):
        where = self.format_where("MetadataPackageVersionId", where)
        return self.push_api.get_subscribers_by_org_key(where, limit)

    def get_push_requests(self, where=None, limit=None):
        where = self.format_where("PackageVersionId", where)
        return self.push_api.get_push_requests(where, limit)

    def get_push_request_objs(self, where=None, limit=None):
        where = self.format_where("PackageVersionId", where)
        return self.push_api.get_push_request_objs(where, limit)

    def get_push_requests_by_id(self, where=None, limit=None):
        where = self.format_where("PackageVersionId", where)
        return self.push_api.get_push_requests_by_id(where, limit)


class PackagePushJob(BasePushApiObject):
    def __init__(self, push_api, request, org, status, sf_id=None):
        self.push_api = push_api
        self.request = request
        self.org = org
        self.status = status
        self.sf_id = sf_id

    def get_push_errors(self, where=None, limit=None):
        where = self.format_where("PackagePushJobId", where)
        return self.push_api.get_push_errors(where, limit)

    def get_push_error_objs(self, where=None, limit=None):
        where = self.format_where("PackagePushJobId", where)
        return self.push_api.get_push_error_objs(where, limit)

    def get_push_errors_by_id(self, where=None, limit=None):
        where = self.format_where("PackagePushJobId", where)
        return self.push_api.get_push_errors_by_id(where, limit)


class PackagePushError(BasePushApiObject):
    def __init__(
        self, push_api, job, severity, error_type, title, message, details, sf_id=None
    ):
        self.push_api = push_api
        self.sf_id = sf_id
        self.job = job
        self.severity = severity
        self.error_type = error_type
        self.title = title
        self.message = message
        self.details = details


class PackagePushRequest(BasePushApiObject):
    def __init__(self, push_api, version, start_time, status, sf_id=None):
        self.push_api = push_api
        self.sf_id = sf_id
        self.version = version
        self.start_time = start_time
        self.status = status

    def get_push_jobs(self, where=None, limit=None):
        where = self.format_where("PackagePushRequestId", where)
        return self.push_api.get_push_jobs(where, limit)

    def get_push_job_objs(self, where=None, limit=None):
        where = self.format_where("PackagePushRequestId", where)
        return self.push_api.get_push_job_objs(where, limit)

    def get_push_jobs_by_id(self, where=None, limit=None):
        where = self.format_where("PackagePushRequestId", where)
        return self.push_api.get_push_jobs_by_id(where, limit)


class PackageSubscriber(object):
    def __init__(
        self,
        push_api,
        version,
        status,
        org_name,
        org_key,
        org_status,
        org_type,
        sf_id=None,
    ):
        self.push_api = push_api
        self.sf_id = sf_id
        self.version = version
        self.status = status
        self.org_name = org_name
        self.org_key = org_key
        self.org_status = org_status
        self.org_type = org_type

    def format_where(self, id_field, where=None):
        base_where = "%s = '%s'" % (id_field, self.org_key)
        if where:
            where = "%s AND (%s)" % (base_where, where)
        else:
            where = base_where
        return where

    def get_push_jobs(self, where=None, limit=None):
        where = self.format_where("SubscriberOrganizationKey", where)
        return self.push_api.get_push_jobs(where, limit)

    def get_push_job_objs(self, where=None, limit=None):
        where = self.format_where("SubscriberOrganizationKey", where)
        return self.push_api.get_push_job_objs(where, limit)

    def get_push_jobs_by_id(self, where=None, limit=None):
        where = self.format_where("SubscriberOrganizationKey", where)
        return self.push_api.get_push_jobs_by_id(where, limit)


class SalesforcePushApi(object):
    """API Wrapper for the Salesforce Push API"""

    def __init__(
        self, sf, logger, lazy=None, default_where=None, batch_size=None, bulk=None
    ):
        self.sf = sf
        self.logger = logger

        if not lazy:
            lazy = []
        self.lazy = lazy

        if not default_where:
            default_where = {}
        self.default_where = default_where

        if not batch_size:
            batch_size = 200
        self.batch_size = batch_size

        self.bulk = bulk

    def return_query_records(self, query, field_names=None, sobject=None):
        res = []
        if self.bulk and field_names and sobject:
            step = BulkApiQueryOperation(
                sobject=sobject, api_options={}, context=self, query=query
            )
            step.query()
            for row in step.get_results():
                res.append(dict(zip(field_names, row)))
            return res
        else:
            res = self.sf.query_all(query)
            if res["totalSize"] > 0:
                return res["records"]
            else:
                return []

    def format_where_clause(self, where, obj=None):
        if obj and obj in self.default_where:
            default_where = self.default_where[obj]
            if where:
                where = "(%s) AND (%s)" % (default_where, where)
            else:
                where = "(%s)" % default_where
        if where:
            where = " WHERE %s" % where
        else:
            where = ""
        return where

    def add_query_limit(self, query, limit):
        if not limit:
            return query

        return "%s LIMIT %s" % (query, limit)

    @lru_cache(32)
    def get_packages(self, where=None, limit=None):
        where = self.format_where_clause(where)
        query = f"SELECT id, name, namespaceprefix FROM MetadataPackage{where}"
        query = self.add_query_limit(query, limit)
        return self.return_query_records(query)

    @lru_cache(32)
    def get_package_objs(self, where=None, limit=None):
        package_objs = []
        for package in self.get_packages(where, limit):
            package_objs.append(
                MetadataPackage(
                    push_api=self,
                    sf_id=package["Id"],
                    name=package["Name"],
                    namespace=package["NamespacePrefix"],
                )
            )
        return package_objs

    @lru_cache(32)
    def get_packages_by_id(self, where=None, limit=None):
        packages = {}
        for package in self.get_package_objs(where, limit):
            packages[package.sf_id] = package
        return packages

    @lru_cache(32)
    def get_package_versions(self, where=None, limit=None):
        where = self.format_where_clause(where)
        query = (
            "SELECT Id, Name, MetadataPackageId, ReleaseState, MajorVersion, MinorVersion, PatchVersion, BuildNumber FROM MetadataPackageVersion%s ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion, BuildNumber DESC"
            % where
        )
        query = self.add_query_limit(query, limit)
        return self.return_query_records(query)

    @lru_cache(32)
    def get_package_version_objs(self, where=None, limit=None):
        package_version_objs = []
        packages = self.get_packages_by_id()
        for package_version in self.get_package_versions(where, limit):
            package_version_objs.append(
                MetadataPackageVersion(
                    push_api=self,
                    name=package_version["Name"],
                    package=packages[package_version["MetadataPackageId"]],
                    state=package_version["ReleaseState"],
                    major=package_version["MajorVersion"],
                    minor=package_version["MinorVersion"],
                    patch=package_version["PatchVersion"],
                    build=package_version["BuildNumber"],
                    sf_id=package_version["Id"],
                )
            )
        return package_version_objs

    @lru_cache(32)
    def get_package_versions_by_id(self, where=None, limit=None):
        package_versions = {}
        for package_version in self.get_package_version_objs(where, limit):
            package_versions[package_version.sf_id] = package_version
        return package_versions

    @lru_cache(32)
    def get_subscribers(self, where=None, limit=None):
        where = self.format_where_clause(where, obj="PackageSubscriber")
        field_names = [
            "Id",
            "MetadataPackageVersionId",
            "InstalledStatus",
            "InstanceName",
            "OrgName",
            "OrgKey",
            "OrgStatus",
            "OrgType",
        ]
        query = f"SELECT {', '.join(field_names)} from PackageSubscriber{where}"
        query = self.add_query_limit(query, limit)

        return self.return_query_records(
            query, field_names=field_names, sobject="PackageSubscriber"
        )

    @lru_cache(32)
    def get_subscriber_objs(self, where=None, limit=None):
        subscriber_objs = []
        package_versions = self.get_package_versions_by_id()
        for subscriber in self.get_subscribers(where, limit):
            subscriber_objs.append(
                PackageSubscriber(
                    push_api=self,
                    version=package_versions[subscriber["MetadataPackageVersionId"]],
                    status=subscriber["InstalledStatus"],
                    org_name=subscriber["OrgName"],
                    org_key=subscriber["OrgKey"],
                    org_status=subscriber["OrgStatus"],
                    org_type=subscriber["OrgType"],
                    sf_id=subscriber["Id"],
                )
            )
        return subscriber_objs

    @lru_cache(32)
    def get_subscribers_by_org_key(self, where=None, limit=None):
        subscribers = {}
        for subscriber in self.get_subscriber_objs(where, limit):
            subscribers[subscriber.org_key] = subscriber
        return subscribers

    @lru_cache(32)
    def get_push_requests(self, where=None, limit=None):
        sobject = "PackagePushRequest"
        field_names = ["Id", "PackageVersionId", "ScheduledStartTime", "Status"]
        where = self.format_where_clause(where, obj=sobject)
        query = f"SELECT {', '.join(field_names)} FROM {sobject}{where} ORDER BY ScheduledStartTime DESC"
        query = self.add_query_limit(query, limit)
        return self.return_query_records(
            query, field_names=field_names, sobject=sobject
        )

    @lru_cache(32)
    def get_push_request_objs(self, where=None, limit=None):
        push_request_objs = []
        package_versions = self.get_package_versions_by_id()
        for push_request in self.get_push_requests(where, limit):
            push_request_objs.append(
                PackagePushRequest(
                    push_api=self,
                    version=package_versions[push_request["PackageVersionId"]],
                    start_time=push_request["ScheduledStartTime"],
                    status=push_request["Status"],
                    sf_id=push_request["Id"],
                )
            )
        return push_request_objs

    @lru_cache(32)
    def get_push_requests_by_id(self, where=None, limit=None):
        push_requests = {}
        for push_request in self.get_push_request_objs(where, limit):
            push_requests[push_request.sf_id] = push_request
        return push_requests

    @lru_cache(32)
    def get_push_jobs(self, where=None, limit=None):
        where = self.format_where_clause(where)
        field_names = [
            "Id",
            "PackagePushRequestId",
            "SubscriberOrganizationKey",
            "Status",
        ]
        query = f"SELECT {', '.join(field_names)} FROM PackagePushJob{where}"
        query = self.add_query_limit(query, limit)
        return self.return_query_records(
            query, field_names=field_names, sobject="PackagePushJob"
        )

    @lru_cache(32)
    def get_push_job_objs(self, where=None, limit=None):
        push_job_objs = []
        lazy = "subscribers" in self.lazy
        if not lazy:
            subscriberorgs = self.get_subscribers_by_org_key()
        push_requests = self.get_push_requests_by_id()
        for push_job in self.get_push_jobs(where, limit):
            if lazy:
                orgs = self.get_subscriber_objs(
                    "OrgKey = '%s'" % push_job["SubscriberOrganizationKey"]
                )
                if not orgs:
                    org = None
                else:
                    org = orgs[0]
            else:
                if push_job["SubscriberOrganizationKey"] not in subscriberorgs:
                    continue
                else:
                    org = subscriberorgs[push_job["SubscriberOrganizationKey"]]
            push_job_objs.append(
                PackagePushJob(
                    push_api=self,
                    request=push_requests[push_job["PackagePushRequestId"]],
                    org=org,
                    status=push_job["Status"],
                    sf_id=push_job["Id"],
                )
            )
        return push_job_objs

    @lru_cache(32)
    def get_push_jobs_by_id(self, where=None, limit=None):
        push_jobs = {}
        for push_job in self.get_push_job_objs(where, limit):
            push_jobs[push_job.sf_id] = push_job
        return push_jobs

    @lru_cache(32)
    def get_push_errors(self, where=None, limit=None):
        sobject = "PackagePushError"
        where = self.format_where_clause(where)
        field_names = [
            "Id",
            "PackagePushJobId",
            "ErrorSeverity",
            "ErrorType",
            "ErrorTitle",
            "ErrorMessage",
            "ErrorDetails",
        ]
        query = f"SELECT {', '.join(field_names)} FROM {sobject}{where}"
        query = self.add_query_limit(query, limit)
        return self.return_query_records(
            query, field_names=field_names, sobject=sobject
        )

    @lru_cache(32)
    def get_push_error_objs(self, where=None, limit=None):
        push_error_objs = []
        lazy = "jobs" in self.lazy
        if not lazy:
            jobs = self.get_push_jobs_by_id()
        for push_error in self.get_push_errors(where, limit):
            if lazy:
                jobs = self.get_push_job_objs(
                    where="Id = '%s'" % push_error["PackagePushJobId"]
                )
            job = jobs[0] if jobs else None

            push_error_objs.append(
                PackagePushError(
                    push_api=self,
                    job=job,
                    severity=push_error["ErrorSeverity"],
                    error_type=push_error["ErrorType"],
                    title=push_error["ErrorTitle"],
                    message=push_error["ErrorMessage"],
                    details=push_error["ErrorDetails"],
                    sf_id=push_error["Id"],
                )
            )
        return push_error_objs

    @lru_cache(32)
    def get_push_errors_by_id(self, where=None, limit=None):
        push_errors = {}
        for push_error in self.get_push_error_objs(where, limit):
            push_errors[push_error.sf_id] = push_error
        return push_errors

    def create_push_request(self, version, orgs, start):

        # Create the request
        res = self.sf.PackagePushRequest.create(
            {
                "PackageVersionId": version,
                "ScheduledStartTime": start.isoformat(timespec="seconds"),
            }
        )
        request_id = res["id"]

        # remove duplicates
        n_orgs_pre = len(orgs)
        self.logger.info("Found {} orgs".format(n_orgs_pre))
        orgs = set(orgs)
        if len(orgs) < n_orgs_pre:
            self.logger.warning(
                "Removed {} duplicate orgs ({} remain)".format(
                    n_orgs_pre - len(orgs), len(orgs)
                )
            )

        # Schedule the orgs
        batches = batch_list(orgs, self.batch_size)
        scheduled_orgs = 0
        for batch_num, batch in enumerate(batches):
            self.logger.info(
                "Batch {} of {}: Attempting to add {} orgs".format(
                    batch_num + 1, len(batches), len(batch)
                )
            )
            valid_batch = self._add_batch(batch, request_id)
            scheduled_orgs += len(valid_batch)
            self.logger.info(
                "{} orgs successfully added to batch".format(len(valid_batch))
            )
        self.logger.info(
            "Push request {} is populated with {} orgs".format(
                request_id, scheduled_orgs
            )
        )
        return request_id, scheduled_orgs

    def _add_batch(self, batch: list, request_id) -> list:

        # add orgs to batch data
        batch_data = {"records": []}
        for i, org in enumerate(batch):
            batch_data["records"].append(
                {
                    "attributes": {"type": "PackagePushJob", "referenceId": org},
                    "PackagePushRequestId": request_id,
                    "SubscriberOrganizationKey": org,
                }
            )

        # add batch to push request
        try:
            self.sf._call_salesforce(
                "POST",
                self.sf.base_url + "composite/tree/PackagePushJob",
                data=json.dumps(batch_data),
            )
        except SalesforceMalformedRequest as e:
            invalid_orgs = set()
            retry_all = False
            for result in e.content["results"]:
                for error in result["errors"]:
                    if "Something bad has happened" in error["message"]:
                        retry_all = True
                        break
                    if error["statusCode"] in [
                        "DUPLICATE_VALUE",
                        "INVALID_OPERATION",
                        "UNKNOWN_EXCEPTION",
                    ]:
                        org_id = result["referenceId"]
                        invalid_orgs.add(org_id)
                        self.logger.info(
                            "Skipping org {} - {}".format(org_id, error["message"])
                        )
                    else:
                        raise
                if retry_all:
                    break
            if retry_all:
                self.logger.warning("Retrying batch")
                batch = self._add_batch(batch, request_id)
            else:
                for org_id in invalid_orgs:
                    batch.remove(org_id)
                if batch:
                    self.logger.warning("Retrying batch without invalid orgs")
                    batch = self._add_batch(batch, request_id)
                else:
                    self.logger.error("Skipping batch (no valid orgs)")
        return batch

    def cancel_push_request(self, request_id):
        return self.sf.PackagePushRequest.update(request_id, {"Status": "Canceled"})

    def run_push_request(self, request_id):
        # Set the request to Pending status
        return self.sf.PackagePushRequest.update(request_id, {"Status": "Pending"})
