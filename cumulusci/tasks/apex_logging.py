""" CumulusCI helper to enable, retrieve, and parse salesforce debug logs."""

import re
import datetime

from cumulusci.tasks.util import decode_to_unicode
from cumulusci.tasks.util import log_time_delta
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class ApexLogger(object):
    """ Apex logging services as a context manager:

    example usage:

    with ApexLogger(self.tooling, profiling='DEBUG') as apexlog:
        self._run_task()

    pprint.pprint(apexlog.logs)

    HUGE TODO: parse the logs
    """

    def __init__(self, task, **kwargs):
        # type: (BaseSalesforceApiTask, **str) -> None
        # from BaseSalesforceApiTask we use the:
        #   * logger
        #   * tooling.query
        #   * get_tooling_object
        self.task = task
        self.user_id = self.task.org_config.user_id
        self.debug_level_id = None
        self.trace_flag_id = None
        self.most_recent_log_id = None
        self.logger = self.task.logger
        self.logs = {}

        if kwargs is None:
            kwargs = {}

        self.debug_level = {
            'ApexCode': kwargs.get('apex', 'Info'),
            'ApexProfiling': kwargs.get('profiling', 'Debug'),
            'Callout': kwargs.get('callout', 'Info'),
            'Database': kwargs.get('database', 'Info'),
            'DeveloperName': kwargs.get('developer_name', 'CumulusCI'),
            'MasterLabel': kwargs.get('label', 'CumulusCI'),
            'System': kwargs.get('system', 'Info'),
            'Validation': kwargs.get('validation', 'Info'),
            'Visualforce': kwargs.get('visualforce', 'Info'),
            'Workflow': kwargs.get('workflow', 'Info'),
        }

    def __enter__(self):
        self._delete_debug_level()
        self._remove_trace_flags()
        self._create_debug_level()
        self._create_trace_flag()
        self._get_most_recent_log()

        return self

    def __exit__(self, *args):
        # we don't care if the context had an exception
        # and we do not return, so the runtime handles it up stack
        self.logs = self._get_logs_since()
        self._delete_debug_level()
        self.most_recent_log_id = None

    def _create_debug_level(self):
        """ create the DebugLevel sobject based on options """
        self.logger.info('Creating DebugLevel object')
        DebugLevel = self.task.get_tooling_object('DebugLevel')
        result = DebugLevel.create(self.debug_level)
        self.debug_level_id = result['id']

    def _create_trace_flag(self):
        self.logger.info('Setting up trace flag to capture debug logs')
        # New TraceFlag expires 12 hours from now
        expiration_date = (datetime.datetime.utcnow() +
                           datetime.timedelta(seconds=60 * 60 * 12))
        TraceFlag = self.task.get_tooling_object('TraceFlag')
        result = TraceFlag.create({
            'DebugLevelId': self.debug_level_id,
            'ExpirationDate': expiration_date.isoformat(),
            'LogType': 'USER_DEBUG',
            'TracedEntityId': self.user_id,
        })
        self.trace_flag_id = result['id']
        self.logger.info('Created TraceFlag for user')

    def _delete_debug_level(self):
        """ Remove existing debug level from the org """

        self.logger.info('Deleting existing DebugLevel objects')
        result = self.task.tooling.query(
            'Select Id from DebugLevel WHERE DeveloperName = \'{}\''.format(
                self.debug_level['DeveloperName']
            )
        )
        if result['totalSize']:
            DebugLevel = self.task.get_tooling_object('DebugLevel')
            for record in result['records']:
                DebugLevel.delete(str(record['Id']))

    def _get_most_recent_log(self):
        """ retrieve the ID of the most recent log for the running user """

        result = self.task.tooling.query(
            "SELECT Id FROM ApexLog WHERE LogUserId = '{}' "
            "ORDER BY SystemModstamp DESC LIMIT 1".format(
                self.user_id
            )
        )
        if result['totalSize']:
            self.most_recent_log_id = result['records'][0]['Id']

    def _get_logs_since(self):
        """ Get the logs since the context manager was entered """

        # TODO: is this the best way of adding this?
        extra_where = ''
        if self.most_recent_log_id:
            extra_where = 'AND Id > \'{}\''.format(self.most_recent_log_id)

        result = self.task.tooling.query_all(
            'SELECT Id, Application, DurationMilliseconds, Location, '
            'LogLength, LogUserId, Operation, Request, StartTime, Status '
            'FROM ApexLog WHERE LogUserId = \'{}\' {}'.format(
                self.user_id, extra_where)
        )

        logs = {}
        for log in result['records']:
            body_url = '{}sobjects/ApexLog/{}/Body'.format(
                self.task.tooling.base_url, log['Id'])
            response = self.task.tooling.request.get(body_url,
                                                     headers=self.task.tooling.headers)
            logs[log['Id']] = decode_to_unicode(response.content)

        return logs

    def _remove_trace_flags(self):
        """ Remove all existing traceflags for the running user. """

        self.logger.info('Deleting existing TraceFlag objects')
        result = self.task.tooling.query(
            "Select Id from TraceFlag Where TracedEntityId = '{}'".format(
                self.user_id
            )
        )
        if result['totalSize']:
            TraceFlag = self.task.get_tooling_object('TraceFlag')
            for record in result['records']:
                TraceFlag.delete(str(record['Id']))


class StartApexLoggingTask(BaseSalesforceApiTask):
    """Start apex logging in an org."""
    task_options = {
        'profiling': {'description': 'The ApexProfiling log level'},
        'apexcode': {'description': 'The ApexCode log level'},
        'callout': {'description': 'The Callout log level'},
        'database': {'description': 'The database log level'},
        'system': {'description': 'The System log level'},
        'validation': {'description': 'The Validation log level'},
        'visualforce': {'description': 'The Visualforce log level'},
        'workflow': {'description': 'The Workflow log level'},
    }

    def _run_task(self):
        self.apex_logs = ApexLogger(self,
                                    profiling=self.options.get(
                                        'profiling', None),
                                    apex=self.options.get('apexcode', None),
                                    callout=self.options.get('callout', None),
                                    database=self.options.get(
                                        'database', None),
                                    system=self.options.get('system', None),
                                    validation=self.options.get(
                                        'validation', None),
                                    visualforce=self.options.get(
                                        'visualforce', None),
                                    workflow=self.options.get('workflow', None),)
        self.apex_logs.__enter__()


class StopApexLoggingTask(BaseSalesforceApiTask):
    """Stop apex logging in an org."""
    def _run_task(self):
        self.apex_logs = ApexLogger(self)
        self.apex_logs._delete_debug_level()


class SalesforceLog(object):
    """ Represents a log. 

    The log file format is described, loosely, at:
    https://help.salesforce.com/articleView?id=code_setting_debug_log_levels.htm



    """

    def _extract_profiling_info(self, log):
        """ given a log file, extract the cumulative limits and profiling """
        log_lines = log.split('\n')
        profiling_data = {}
        limits_data = {}
        in_limits = False
        in_cumulative_limits = False
        in_profiling = False
        for line in log_lines:
            if '|LIMIT_USAGE_FOR_NS|(default)|' in line:
                # Parse the start of the limits section
                in_limits = True
                continue
            if in_limits and ':' not in line:
                # Parse the end of the limits section
                in_limits = False
                continue
            if in_limits:
                # Parse the limit name, used, and allowed values
                limit, value = line.split(': ')
                used, allowed = value.split(' out of ')
                limits_data[limit] = {'used': used, 'allowed': allowed}
                continue
            if '|CUMULATIVE_PROFILING_BEGIN' in line:
                # parse the start of the profiling limits
                in_profiling = True
                continue
            if '|CUMULATIVE_PROFILING_END' in line:
                in_profiling = False
                continue
            if in_profiling:

                continue
        return (limits_data, profiling_data)

    def _parse_log_by_method(self, class_name, f):
        """Parse an Apex test log by method.

        this is a generator and yields method,stats,children"""
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
            line = decode_to_unicode(line).strip()
            if '|CODE_UNIT_STARTED|[EXTERNAL]|' in line:
                unit, unit_type, unit_info = self._parse_unit_started(
                    class_name, line)
                if unit_type == 'test_method':
                    method = decode_to_unicode(unit)
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
                stats['duration'] = log_time_delta(
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
                stats['duration'] = log_time_delta(
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
