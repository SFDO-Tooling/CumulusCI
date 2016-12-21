import time
from datetime import datetime
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.push.push_api import SalesforcePushApi

class BaseSalesforcePushTask(BaseSalesforceApiTask):
    completed_statuses = ['Succeeded','Failed','Cancelled']

    def _init_task(self):
        super(BaseSalesforcePushTask, self)._init_task()
        self.push = SalesforcePushApi(self.sf, self.logger)

    def _parse_version(self, version):
        # Parse the version number string
        major = None
        minor = None
        patch = None
        build = None
        state = 'Released'
        version_parts = version.split('.')
        if len(version_parts) >= 1:
            major = version_parts[0]
        if len(version_parts) == 2:
            minor = version_parts[1]
            if minor.find('Beta') != -1:
                state = 'Beta'
                minor, build = minor.replace(' (Beta ',',').replace(')','').split(',')
        if len(version_parts) > 2:
            minor = version_parts[1]
            patch = version_parts[2]
            if patch.find('Beta') != -1:
                state = 'Beta'
                patch, build = minor.replace(' (Beta ',',').replace(')','').split(',')
        
        return {
            'major': major,
            'minor': minor,
            'patch': patch,
            'build': build,
            'state': state,
        }

    def _get_version(self, package, version):

        version_info = self._parse_version(version)

        version_where = "ReleaseState = '{}' AND MajorVersion = {} AND MinorVersion = {}".format(
            version_info['state'],
            version_info['major'],
            version_info['minor'],
        )
        if version_info.get('patch'):
             version_where += " AND PatchVersion = {}".format(version_info['patch'])
        if version_info['state'] == 'Beta' and version_info.get('build'):
             version_where += " AND BuildNumber = {}".format(version_info['build'])

        version = package.get_package_version_objs(version_where, limit=1)
        if not version:
            raise PushApiObjectNotFound('PackageVersion not found.  Namespace = {}, Version Info = {}'.format(package.namespace, version_info))
        return version[0]


    def _get_package(self, namespace):
        package = self.push.get_package_objs(
            "NamespacePrefix = '{}'".format(namespace),
            limit=1
        )
        
        if not package:
            raise PushApiObjectNotFound('The package with namespace {} was not found'.format(namespace))

        return package[0]

    def _load_orgs_file(self, path):
        orgs = []
        with open(path, 'r') as f_orgs:
            for org in f_orgs:
                orgs.append(org.strip())
        return orgs

    def _report_push_status(self, request_id):
        default_where = {'PackagePushRequest': "Id = '{}'".format(request_id)}

        # Create a new PushAPI instance with different settings than self.push
        self.push_report = SalesforcePushApi(
            self.sf, 
            self.logger, 
            lazy = ['subscribers','jobs'],
            default_where = default_where,
        )

        # Get the push request
        push_request = self.push_report.get_push_request_objs("Id = '{}'".format(request_id), limit=1)
        if not push_request:
            raise PushApiObjectNotFound('Push Request {} was not found'.format(push_request))
        push_request = push_request[0]


        # Check if the request is complete
        interval = 10
        if push_request.status not in self.completed_statuses:
            self.logger.info(
                'Push request is not yet complete.  Polling for status every {} seconds until completion...'.format(interval)
            )

        # Loop waiting for request completion
        i = 0 
        while push_request.status not in self.completed_statuses:
            if i == 10:
                self.logger.info('This is taking a while! Polling every 60 seconds...')
                interval = 60
            time.sleep(interval)

            # Clear the method level cache on get_push_requests and get_push_request_objs
            self.push_report.get_push_requests.cache.clear()
            self.push_report.get_push_request_objs.cache.clear()

            # Get the push_request again
            push_request = self.push_report.get_push_request_objs("Id = '{}'".format(request_id), limit=1)[0]

            self.logger.info(push_request.status)

            i += 1

        failed_jobs = []
        success_jobs = []
        cancelled_jobs = []

        jobs = push_request.get_push_job_objs()
        for job in jobs:
            if job.status == 'Failed':
                failed_jobs.append(job)
            elif job.status == 'Succeeded':
                success_jobs.append(job)
            elif job.status == 'Cancelled':
                cancelled_jobs.append(job)

        self.logger.info(
            "Push complete: {} succeeded, {} failed, {} cancelled".format(
                len(success_jobs),
                len(failed_jobs),
                len(cancelled_jobs),
            )
        )

        failed_by_error = {}
        for job in failed_jobs:
            errors = job.get_push_error_objs()
            for error in errors:
                error_key = (error.error_type, error.title, error.message, error.details)
                if error_key not in failed_by_error:
                    failed_by_error[error_key] = []
                failed_by_error[error_key].append(error)

        if failed_jobs:
            self.logger.info("-----------------------------------")
            self.logger.info("Failures by error type")
            self.logger.info("-----------------------------------")
            for key, errors in failed_by_error.items():
                self.logger.info("    ")
                self.logger.info("{} failed with...".format(len(errors)))
                self.logger.info("    Error Type = {}".format(key[0]))
                self.logger.info("    Title = {}".format(key[1]))
                self.logger.info("    Message = {}".format(key[2]))
                self.logger.info("    Details = {}".format(key[3]))
        
    
class SchedulePushOrgList(BaseSalesforcePushTask):

    task_options = {
        'orgs': {
            'description': "The path to a file containing one OrgID per line.",
            'required': True,
        },
        'version': {
            'description': "The managed package version to push",
            'required': True,
        },
        'namespace': {
            'description': "The managed package namespace to push. Defaults to project__package__namespace.",
        },
        'start_time': {
            'description': "Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00",
        }
    }

    def _init_options(self, kwargs):
        super(SchedulePushOrgList, self)._init_options(kwargs)

        # Set the namespace option to the value from cumulusci.yml if not already set
        if not 'namespace' in self.options:
            self.options['namespace'] = self.project_config.project__package__namespace

    def _get_orgs(self):
        return self._load_orgs_file(self.options.get('orgs'))

    def _run_task(self):
        orgs = self._get_orgs()
        package = self._get_package(self.options.get('namespace')) 
        version = self._get_version(package, self.options.get('version'))

        start_time = self.options.get('start_time')
        if start_time:
            start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M") # Example: 2016-10-19T10:00

        self.request_id = self.push.create_push_request(version, orgs, start_time)

        if len(orgs) > 1000:
            self.logger.info("Delaying 30 seconds to allow all jobs to initialize...")
            time.sleep(30)

        self.logger.info('Push Request {} is populated with {} orgs'.format(self.request_id, len(orgs)))
        self.logger.info('Setting status to Pending to queue execution.')
        if start_time:
            self.logger.info('The push request will start at {}'.format(start_time))

        # Run the job
        self.logger.info(self.push.run_push_request(self.request_id))
        self.logger.info('Push Request {} is queued for execution.'.format(self.request_id))

        # Report the status
        self._report_push_status(self.request_id)

class SchedulePushOrgQuery(SchedulePushOrgList):
    task_options = {
        'version': {
            'description': "The managed package version to push",
            'required': True,
        },
        'subscriber_where': {
            'description': "A SOQL style where clause for filtering PackageSubscriber objects.  Ex: OrgType = 'Sandbox'",
        },
        'min_version': {
            'description': "If set, no subscriber with a version lower than min_version will be selected for push",
        },
        'namespace': {
            'description': "The managed package namespace to push. Defaults to project__package__namespace.",
        },
        'start_time': {
            'description': "Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00",
        }
    }

    def _get_orgs(self):
        subscriber_where = self.options.get('subscriber_where')
        default_where = {'PackageSubscriber': "OrgStatus = 'Active' AND InstalledStatus = 'i'"}
        if subscriber_where:
            default_where['PackageSubscriber'] += " AND ({})".format(subscriber_where)

        push_api = SalesforcePushApi(self.sf, self.logger, default_where=default_where.copy())

        package = self._get_package(self.options.get('namespace')) 
        version = self._get_version(package, self.options.get('version'))
        min_version = self.options.get('min_version')
        if min_version:
            min_version = self._get_version(package, self.options.get('min_version'))

        orgs = []

        if min_version:
            # If working with a range of versions, use an inclusive search
            versions = version.get_older_released_version_objs(greater_than_version=min_version)
            included_versions = []
            for include_version in versions:
                included_versions.append(str(include_version.sf_id))
            if not included_versions:
                raise ValueError(
                    'No versions found between version id {} and {}'.format(
                        version.version_number, min_version.version_number
                    )
                )

            # Query orgs for each version in the range individually to avoid query timeout errors with querying multiple versions
            for included_version in included_versions:
                # Clear the get_subscribers method cache before each call
                push_api.get_subscribers.cache.clear()
                push_api.default_where['PackageSubscriber'] = "{} AND MetadataPackageVersionId = '{}'".format(
                    default_where['PackageSubscriber'],
                    included_version,
                )
                for subscriber in push_api.get_subscribers():
                    orgs.append(subscriber['OrgKey'])

        else:
            # If working with a specific version rather than a range, use an exclusive search
            # Add exclusion of all orgs running on newer releases
            newer_versions = version.get_newer_released_version_objs()
            excluded_versions = [str(version.sf_id),]
            for newer in newer_versions:
                excluded_versions.append(str(newer.sf_id))
            if len(excluded_versions) == 1:
                push_api.default_where['PackageSubscriber'] += " AND MetadataPackageVersionId != '{}'".format(
                    excluded_versions[0],
                )
            else:
                push_api.default_where['PackageSubscriber'] += " AND MetadataPackageVersionId NOT IN {}".format(
                    "('" + "','".join(excluded_versions) + "')"
                )

            for subscriber in push_api.get_subscribers():
                orgs.append(subscriber['OrgKey'])

        return orgs


