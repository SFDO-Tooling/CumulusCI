import base64
import cgi
import io
import logging
import os
import tempfile
from time import sleep
import zipfile

from simple_salesforce import Salesforce

from cumulusci.core.tasks import BaseTask
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.metadata import ApiRetrieveInstalledPackages
from cumulusci.salesforce_api.metadata import ApiRetrievePackaged
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged


class BaseSalesforceTask(BaseTask):
    name = 'BaseSalesforceTask'
    salesforce_task = True

    def __call__(self):
        self._refresh_oauth_token()
        return self._run_task()

    def _run_task(self):
        raise NotImplementedError(
            'Subclasses should provide their own implementation')

    def _refresh_oauth_token(self):
        self.org_config.refresh_oauth_token(
            self.project_config.keychain.get_connected_app())


class BaseSalesforceMetadataApiTask(BaseSalesforceTask):
    api_class = None
    name = 'BaseSalesforceMetadataApiTask'

    def _get_api(self):
        return self.api_class(self)

    def _run_task(self):
        api = self._get_api()
        if self.options:
            return api(**options)
        else:
            return api()


class BaseSalesforceApiTask(BaseSalesforceTask):
    name = 'BaseSalesforceApiTask'

    def _init_task(self):
        self.sf = self._init_api()

    def _init_api(self):
        return Salesforce(
            instance=self.org_config.instance_url.replace('https://', ''),
            session_id=self.org_config.access_token,
            version=self.project_config.project__package__api_version,
        )


class BaseSalesforceToolingApiTask(BaseSalesforceApiTask):
    name = 'BaseSalesforceToolingApiTask'

    def _init_task(self):
        self.tooling = self._init_api()
        self.tooling.base_url += 'tooling/'

    def _get_tooling_object(self, obj_name):
        obj = getattr(self.tooling, obj_name)
        obj.base_url = obj.base_url.replace('/sobjects/', '/tooling/sobjects/')
        return obj


class GetInstalledPackages(BaseSalesforceMetadataApiTask):
    api_class = ApiRetrieveInstalledPackages
    name = 'GetInstalledPackages'


class RetrieveUnpackaged(BaseSalesforceMetadataApiTask):
    api_class = ApiRetrieveUnpackaged


class RetrievePackaged(BaseSalesforceMetadataApiTask):
    api_class = ApiRetrievePackaged


class Deploy(BaseSalesforceMetadataApiTask):
    api_class = ApiDeploy
    task_options = {
        'path': {
            'description': 'The path to the metadata source to be deployed',
            'required': True,
        }
    }

    def _get_api(self, path=None):
        if not path:
            path = self.task_config.options__path

        # Build the zip file
        zip_file = tempfile.TemporaryFile()
        zipf = zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED)

        pwd = os.getcwd()

        os.chdir(path)
        for root, dirs, files in os.walk('.'):
            for f in files:
                zip_path = os.path.join(root, f)
                zipf.write(os.path.join(root, f))
        zipf.close()
        zip_file.seek(0)
        package_zip = base64.b64encode(zip_file.read())

        os.chdir(pwd)

        return self.api_class(self, package_zip)


class DeployBundles(Deploy):
    task_options = {
        'path': {
            'description': 'The path to the parent directory containing the metadata bundles directories',
            'required': True,
        }
    }

    def _run_task(self):
        path = self.task_config.options__path
        pwd = os.getcwd()

        path = os.path.join(pwd, path)

        self.logger.info(
            'Deploying all metadata bundles in path {}'.format(path))

        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if not os.path.isdir(item_path):
                continue

            self.logger.info('Deploying bundle: {}'.format(item))

            self._deploy_bundle(item_path)

    def _deploy_bundle(self, path):
        api = self._get_api(path)
        if self.options:
            return api(**options)
        else:
            return api()


class RunApexTests(BaseSalesforceToolingApiTask):
    task_options = {
        'test_name_match': {
            'description': ('Query to find Apex test classes to run ' +
                            '("%" is wildcard)'),
            'required': True,
        },
        'test_name_exclude': {
            'description': ('Query to find Apex test classes to exclude ' +
                            '("%" is wildcard)'),
            'required': False,
        },
        'namespace': {
            'description': 'Salesforce project namespace',
            'required': False,
        },
        'poll_interval': {
            'description': 'Time to wait between polling for Apex test status',
            'required': False,
        },
        'junit_output': {
            'description': 'File name for JUnit output',
            'required': False,
        },
    }

    def _decode_to_unicode(self, content):
        if content:
            try:
                # Try to decode ISO-8859-1 to unicode
                return content.decode('ISO-8859-1')
            except UnicodeEncodeError:
                # Assume content is unicode already
                return content

    def _get_test_classes(self):
        namespace = self.options.get('namespace')
        if namespace:
            namespace = "'{}'".format(namespace)
        else:
            namespace = 'null'
        # Split by commas to allow multiple class name matching options
        test_name_match = self.options['test_name_match']
        included_tests = []
        for pattern in test_name_match.split(','):
            if pattern:
                included_tests.append("Name LIKE '{}'".format(pattern))
        # Add any excludes to the where clause
        test_name_exclude = self.options.get('test_name_exclude', '')
        excluded_tests = []
        for pattern in test_name_exclude.split(','):
            if pattern:
                excluded_tests.append("(NOT Name LIKE '{}')".format(pattern))
        # Get all test classes for namespace
        query = ('SELECT Id, Name FROM ApexClass ' +
                 'WHERE NamespacePrefix = {}'.format(namespace))
        if included_tests:
            query += ' AND ({})'.format(' OR '.join(included_tests))
        if excluded_tests:
            query += ' AND {}'.format(' AND '.join(excluded_tests))
        # Run the query
        self.logger.info('Running query: {}'.format(query))
        result = self.tooling.query_all(query)
        self.logger.info('Found {} test classes'.format(result['totalSize']))
        return result

    def _get_test_results(self, job_id, classes_by_id, results_by_class_name,
                          classes_by_name):
        result = self.tooling.query_all("SELECT StackTrace, Message, " +
            "ApexLogId, AsyncApexJobId, MethodName, Outcome, ApexClassId, " +
            "TestTimestamp FROM ApexTestResult " +
            "WHERE AsyncApexJobId = '{}'".format(job_id))
        counts = {
            'Pass': 0,
            'Fail': 0,
            'CompileFail': 0,
            'Skip': 0,
        }
        for record in result['records']:
            class_name = classes_by_id[record['ApexClassId']]
            results_by_class_name[class_name][record['MethodName']] = record
            counts[record['Outcome']] += 1
        test_results = []
        class_names = results_by_class_name.keys()
        class_names.sort()
        for class_name in class_names:
            class_id = classes_by_name[class_name]
            duration = None
            self.logger.info(u'Class: {}'.format(class_name))
            method_names = results_by_class_name[class_name].keys()
            method_names.sort()
            for method_name in method_names:
                result = results_by_class_name[class_name][method_name]
                self.logger.info(u'\t{Outcome}: {MethodName}'.format(**result))
                test_results.append({
                    'Children': result.get('children', None),
                    'ClassName': self._decode_to_unicode(class_name),
                    'Method': self._decode_to_unicode(result['MethodName']),
                    'Message': self._decode_to_unicode(result['Message']),
                    'Outcome': self._decode_to_unicode(result['Outcome']),
                    'StackTrace': self._decode_to_unicode(
                        result['StackTrace']),
                    'Stats': result.get('stats', None),
                    'TestTimestamp': result.get('TestTimestamp', None),
                })
                if result['Outcome'] in ['Fail', 'CompileFail']:
                    self.logger.info(u'\tMessage: {Message}'.format(**result))
                    self.logger.info(u'\tStackTrace: {StackTrace}'.format(
                        **result))
        self.logger.info(u'-' * 80)
        self.logger.info(u'Pass: {}  Fail: {}  CompileFail: {}  Skip: {}'
                         .format(
                             counts['Pass'],
                             counts['Fail'],
                             counts['CompileFail'],
                             counts['Skip'],
                         ))
        self.logger.info(u'-' * 80)
        if counts['Fail'] or counts['CompileFail']:
            self.logger.info(u'-' * 80)
            self.logger.info(u'Failing Tests')
            self.logger.info(u'-' * 80)
            counter = 0
            for result in test_results:
                if result['Outcome'] not in ['Fail', 'CompileFail']:
                    continue
                counter += 1
                self.logger.info(u'{}: {}.{} - {}'.format(counter,
                    result['ClassName'], result['Method'], result['Outcome']))
                self.logger.info(u'\tMessage: {}'.format(result['Message']))
                self.logger.info(u'\tStackTrace: {}'.format(
                    result['StackTrace']))
        return test_results

    def _run_task(self):
        result = self._get_test_classes()
        if result['totalSize'] == 0:
            return
        classes_by_id = {}
        classes_by_name = {}
        trace_id = None
        results_by_class_name = {}
        classes_by_log_id = {}
        logs_by_class_id = {}
        for record in result['records']:
            classes_by_id[record['Id']] = record['Name']
            classes_by_name[record['Name']] = record['Id']
            results_by_class_name[record['Name']] = {}
        self.logger.info('Queuing tests for execution...')
        ids = classes_by_id.keys()
        job_id = self.tooling.restful('runTestsAsynchronous',
            params={'classids': ','.join(str(id) for id in ids)})
        self._wait_for_tests(job_id)
        test_results = self._get_test_results(
            job_id, classes_by_id, results_by_class_name, classes_by_name)
        self._write_output(test_results)

    def _wait_for_tests(self, job_id):
        poll_interval = int(self.options.get('poll_interval', 1))
        while True:
            result = self.tooling.query_all(
                "SELECT Id, Status, ApexClassId FROM ApexTestQueueItem " +
                "WHERE ParentJobId = '{}'".format(job_id))
            counts = {
                'Aborted': 0,
                'Completed': 0,
                'Failed': 0,
                'Holding': 0,
                'Preparing': 0,
                'Processing': 0,
                'Queued': 0,
            }
            for record in result['records']:
                counts[record['Status']] += 1
            self.logger.info('Completed: {}  Processing: {}  Queued: {}'
                             .format(
                                 counts['Completed'],
                                 counts['Processing'],
                                 counts['Queued'],
                             ))
            if counts['Queued'] == 0 and counts['Processing'] == 0:
                self.logger.info('Apex tests completed')
                break
            sleep(poll_interval)

    def _write_output(self, test_results):
        filename = self.options['junit_output']
        with io.open(filename, mode='w', encoding='utf-8') as f:
            f.write(u'<testsuite tests="{}">\n'.format(len(test_results)))
            for result in test_results:
                s = u'  <testcase classname="{}" name="{}"'.format(
                    result['ClassName'], result['Method'])
                if ('Stats' in result and result['Stats']
                        and 'duration' in result['Stats']):
                    s += ' time="{}"'.format(result['Stats']['duration'])
                if result['Outcome'] in ['Fail', 'CompileFail']:
                    s += '>\n'
                    s += '    <failure type="{}">{}</failure>\n'.format(
                        cgi.escape(result['StackTrace']),
                        cgi.escape(result['Message']),
                    )
                    s += '  </testcase>\n'
                else:
                    s += ' />\n'
                f.write(s)
            f.write(u'</testsuite>')
