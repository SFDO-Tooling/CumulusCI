import base64
import cgi
import datetime
import io
import json
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
        self._init_class()

    def _init_class(self):
        pass

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

    def _init_class(self):
        self.classes_by_id = {}
        self.classes_by_name = {}
        self.job_id = None
        self.results_by_class_name = {}
        self._debug_init_class()

    # These are overridden in the debug version
    def _debug_init_class(self):
        pass

    def _debug_get_duration_class(self, class_id):
        pass

    def _debug_get_duration_method(self, result):
        pass

    def _debug_get_logs(self):
        pass

    def _debug_get_results(self, result):
        pass

    def _debug_create_trace_flag(self):
        pass

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

    def _get_test_results(self):
        result = self.tooling.query_all("SELECT StackTrace, Message, " +
            "ApexLogId, AsyncApexJobId, MethodName, Outcome, ApexClassId, " +
            "TestTimestamp FROM ApexTestResult " +
            "WHERE AsyncApexJobId = '{}'".format(self.job_id))
        counts = {
            'Pass': 0,
            'Fail': 0,
            'CompileFail': 0,
            'Skip': 0,
        }
        for test_result in result['records']:
            class_name = self.classes_by_id[test_result['ApexClassId']]
            self.results_by_class_name[class_name][test_result[
                'MethodName']] = test_result
            counts[test_result['Outcome']] += 1
            self._debug_get_results(test_result)
        self._debug_get_logs()
        test_results = []
        class_names = self.results_by_class_name.keys()
        class_names.sort()
        for class_name in class_names:
            class_id = self.classes_by_name[class_name]
            message = 'Class: {}'.format(class_name)
            duration = self._debug_get_duration_class(class_id)
            if duration:
                message += '({}s)'.format(duration)
            self.logger.info(message)
            method_names = self.results_by_class_name[class_name].keys()
            method_names.sort()
            for method_name in method_names:
                result = self.results_by_class_name[class_name][method_name]
                message = '\t{}: {}'.format(result['Outcome'],
                    result['MethodName'])
                duration = self._debug_get_duration_method(result)
                if duration:
                    message += ' ({}s)'.format(duration)
                self.logger.info(message)
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
                    self.logger.info('\tMessage: {}'.format(result['Message']))
                    self.logger.info('\tStackTrace: {}'.format(
                        result['StackTrace']))
        self.logger.info('-' * 80)
        self.logger.info('Pass: {}  Fail: {}  CompileFail: {}  Skip: {}'
                         .format(
                             counts['Pass'],
                             counts['Fail'],
                             counts['CompileFail'],
                             counts['Skip'],
                         ))
        self.logger.info('-' * 80)
        if counts['Fail'] or counts['CompileFail']:
            self.logger.info('-' * 80)
            self.logger.info('Failing Tests')
            self.logger.info('-' * 80)
            counter = 0
            for result in test_results:
                if result['Outcome'] not in ['Fail', 'CompileFail']:
                    continue
                counter += 1
                self.logger.info('{}: {}.{} - {}'.format(counter,
                    result['ClassName'], result['Method'], result['Outcome']))
                self.logger.info('\tMessage: {}'.format(result['Message']))
                self.logger.info('\tStackTrace: {}'.format(
                    result['StackTrace']))
        return test_results

    def _run_task(self):
        result = self._get_test_classes()
        if result['totalSize'] == 0:
            return
        for test_class in result['records']:
            self.classes_by_id[test_class['Id']] = test_class['Name']
            self.classes_by_name[test_class['Name']] = test_class['Id']
            self.results_by_class_name[test_class['Name']] = {}
        self._debug_create_trace_flag()
        self.logger.info('Queuing tests for execution...')
        ids = self.classes_by_id.keys()
        self.job_id = self.tooling.restful('runTestsAsynchronous',
            params={'classids': ','.join(str(id) for id in ids)})
        self._wait_for_tests()
        test_results = self._get_test_results()
        self._write_output(test_results)

    def _wait_for_tests(self):
        poll_interval = int(self.options.get('poll_interval', 1))
        while True:
            result = self.tooling.query_all(
                "SELECT Id, Status, ApexClassId FROM ApexTestQueueItem " +
                "WHERE ParentJobId = '{}'".format(self.job_id))
            counts = {
                'Aborted': 0,
                'Completed': 0,
                'Failed': 0,
                'Holding': 0,
                'Preparing': 0,
                'Processing': 0,
                'Queued': 0,
            }
            for test_queue_item in result['records']:
                counts[test_queue_item['Status']] += 1
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
        results_filename = self.options['results_filename']
        with io.open(results_filename, mode='w', encoding='utf-8') as f:
            f.write(u'<testsuite tests="{}">\n'.format(len(test_results)))
            for result in test_results:
                s = '  <testcase classname="{}" name="{}"'.format(
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
                f.write(unicode(s))
            f.write(u'</testsuite>')


class RunApexTestsDebug(RunApexTests):
    """Run Apex tests and collect debug info"""

    def _debug_init_class(self):
        self.classes_by_log_id = {}
        self.logs_by_class_id = {}
        self.tooling.TraceFlag.base_url = (
            'https://{}/services/data/v{}/tooling/sobjects/{}/'.format(
            self.tooling.sf_instance, self.tooling.sf_version, 'TraceFlag'))
        self.trace_id = None

    def _debug_create_trace_flag(self):
        """Create a TraceFlag for a given user."""
        self._delete_trace_flags()
        self.logger.info('Setting up trace flag to capture debug logs')
        # New TraceFlag expires 12 hours from now
        expiration_date = (datetime.datetime.now() +
            datetime.timedelta(seconds=60*60*12))
        result = self.tooling.TraceFlag.create({
            'ApexCode': 'Info',
            'ApexProfiling': 'Debug',
            'Callout': 'Info',
            'Database': 'Info',
            'ExpirationDate': expiration_date.isoformat(),
            'System': 'Info',
            'TracedEntityId': self.org_config.user_id,
            'Validation': 'Info',
            'Visualforce': 'Info',
            'Workflow': 'Info',
        })
        self.trace_id = result['id']
        self.logger.info('Created TraceFlag for user')

    def _delete_trace_flags(self):
        """Delete existing TraceFlags."""
        self.logger.info('Deleting existing TraceFlags')
        traceflags = self.tooling.query('Select Id from TraceFlag')
        if traceflags['totalSize']:
            for traceflag in traceflags['records']:
                self.tooling.TraceFlag.delete(str(traceflag['Id']))

    def _debug_get_duration_class(self, class_id):
        if class_id in self.logs_by_class_id:
            return int(self.logs_by_class_id[class_id][
                'DurationMilliseconds']) * .001

    def _debug_get_duration_method(self, result):
        if result.get('stats') and 'duration' in result['stats']:
            return result['stats']['duration']

    def _debug_get_logs(self):
        log_ids = "('{}')".format(
            "','".join(str(id) for id in self.classes_by_log_id.keys()))
        result = self.tooling.query_all('SELECT Id, Application, ' +
            'DurationMilliseconds, Location, LogLength, LogUserId, ' +
            'Operation, Request, StartTime, Status ' +
            'from ApexLog where Id in {}'.format(log_ids))
        for log in result['records']:
            class_id = self.classes_by_log_id[log['Id']]
            class_name = self.classes_by_id[class_id]
            self.logs_by_class_id[class_id] = log
            body_url = '{}sobjects/ApexLog/{}/Body'.format(
                self.tooling.base_url, log['Id'])
            response = self.tooling.request.get(body_url,
                headers=self.tooling.headers)
            log_file = class_name + '.log'
            debug_log_dir = self.options.get('debug_log_dir')
            if debug_log_dir:
                log_file = os.path.join(debug_log_dir, log_file)
            with io.open(log_file, mode='w', encoding='utf-8') as f:
                f.write(unicode(response.content))
            with io.open(log_file, mode='r', encoding='utf-8') as f:
                method_stats = self._parse_log(class_name, f)
            # Add method stats to results_by_class_name
            for method, info in method_stats.items():
                results_by_class_name[class_name][method].update(info)
        # Delete the TraceFlag
        self.tooling.TraceFlag.delete(str(self.trace_id))

    def _debug_get_results(self, result):
        if result['ApexLogId']:
            self.classes_by_log_id[result['ApexLogId']] = result['ApexClassId']

    def _log_time_delta(self, start, end):
        """
        Returns microsecond difference between two debug log timestamps in the
        format HH:MM:SS.micro.
        """
        dummy_date = datetime.date(2001, 1, 1)
        dummy_date_next = datetime.date(2001, 1, 2)
        # Split out the parts of the start and end string
        start_parts = re.split(':|\.', start)
        start_parts = [int(part) for part in start_parts]
        start_parts[3] = start_parts[3] * 1000
        t_start = datetime.time(*start_parts)
        end_parts = re.split(':|\.', end)
        end_parts = [int(part) for part in end_parts]
        end_parts[3] = end_parts[3] * 1000
        t_end = datetime.time(*end_parts)
        # Combine with dummy date to do date math
        d_start = datetime.datetime.combine(dummy_date, t_start)
        # If end was on the next day, attach to next dummy day
        if start_parts[0] > end_parts[0]:
            d_end = datetime.datetime.combine(dummy_date_next, t_end)
        else:
            d_end = datetime.datetime.combine(dummy_date, t_end)
        delta = d_end - d_start
        return delta.total_seconds()

    def _parse_log(self, class_name, f):
        """Parse an Apex test log."""
        class_name = self._decode_to_unicode(class_name)
        methods = {}
        for method, stats, children in self._parse_log_by_method(class_name,
                f):
            methods[method] = {'stats': stats, 'children': children}
        return methods

    def _parse_log_by_method(self, class_name, f):
        """Parse an Apex test log by method."""
        stats = {}
        last_stats = {}
        in_limits = False
        in_cumulative_limits = False
        in_testing_limits = False
        unit = None
        method = None
        children = {}
        parent = None
        for line in f:
            line = self._decode_to_unicode(line).strip()
            if '|CODE_UNIT_STARTED|[EXTERNAL]|' in line:
                unit, unit_type, unit_info = self._parse_unit_started(
                    class_name, line)
                if unit_type == 'test_method':
                    method = self._decode_to_unicode(unit)
                    method_unit_info = unit_info
                    children = []
                    stack = []
                else:
                    stack.append({
                        'unit': unit,
                        'unit_type': unit_type,
                        'unit_info': unit_info,
                        'stats': {},
                        'children': [],
                    })
                continue
            if '|CUMULATIVE_LIMIT_USAGE' in line and 'USAGE_END' not in line:
                in_cumulative_limits = True
                in_testing_limits = False
                continue
            if '|TESTING_LIMITS' in line:
                in_testing_limits = True
                in_cumulative_limits = False
                continue
            if '|LIMIT_USAGE_FOR_NS|(default)|' in line:
                # Parse the start of the limits section
                in_limits = True
                continue
            if in_limits and ':' not in line:
                # Parse the end of the limits section
                in_limits = False
                in_cumulative_limits = False
                in_testing_limits = False
                continue
            if in_limits:
                # Parse the limit name, used, and allowed values
                limit, value = line.split(': ')
                if in_testing_limits:
                    limit = 'TESTING_LIMITS: {}'.format(limit)
                used, allowed = value.split(' out of ')
                stats[limit] = {'used': used, 'allowed': allowed}
                continue
            if '|CODE_UNIT_FINISHED|{}.{}'.format(class_name, method) in line:
                # Handle the finish of test methods
                end_timestamp = line.split(' ')[0]
                stats['duration'] = self._log_time_delta(
                    method_unit_info['start_timestamp'], end_timestamp)
                # Yield the stats for the method
                yield method, stats, children
                last_stats = stats.copy()
                stats = {}
                in_cumulative_limits = False
                in_limits = False
            elif '|CODE_UNIT_FINISHED|' in line:
                # Handle all other code units finishing
                end_timestamp = line.split(' ')[0]
                stats['duration'] = self._log_time_delta(
                    method_unit_info['start_timestamp'], end_timestamp)
                try:
                    child = stack.pop()
                except:
                    # Skip if there was no stack. This seems to have have
                    # started in Spring 16 where the debug log will contain
                    # CODE_UNIT_FINISHED lines which have no matching
                    # CODE_UNIT_STARTED from earlier in the file.
                    continue
                child['stats'] = stats
                if not stack:
                    # Add the child to the main children list
                    children.append(child)
                else:
                    # Add this child to its parent
                    stack[-1]['children'].append(child)
                stats = {}
                in_cumulative_limits = False
                in_limits = False
            if '* MAXIMUM DEBUG LOG SIZE REACHED *' in line:
                # If debug log size limit was reached, fail gracefully
                break

    def _parse_unit_started(self, class_name, line):
        unit = line.split('|')[-1]
        unit_type = 'other'
        unit_info = {}
        if unit.startswith(class_name + '.'):
            unit_type = 'test_method'
            unit = unit.split('.')[-1]
        elif 'trigger event' in unit:
            unit_type = 'trigger'
            unit, obj, event = re.match(
                r'(.*) on (.*) trigger event (.*) for.*', unit).groups()
            unit_info = {'event': event, 'object': obj}
        # Add the start timestamp to unit_info
        unit_info['start_timestamp'] = line.split(' ')[0]
        return unit, unit_type, unit_info

    def _write_output(self, test_results):
        results_filename = self.options['results_filename']
        with io.open(results_filename, mode='w', encoding='utf-8') as f:
            f.write(unicode(json.dumps(test_results)))
