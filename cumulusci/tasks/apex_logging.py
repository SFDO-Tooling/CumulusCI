
import datetime


def decode_to_unicode(content):
    if content:
        try:
            # Try to decode ISO-8859-1 to unicode
            return content.decode('ISO-8859-1')
        except UnicodeEncodeError:
            # Assume content is unicode already
            return content


class ApexLogger(object):
    """ Apex logging services as a context manager:

    example usage:
    with ApexLogger(self.tooling, profiling='DEBUG') as l:
        self._run_task()
        results = l.get_logs()

    dostuffwith(results)

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
        """ Remove all debug levels from the org """
        # TODO: be more selective?
        self.logger.info('Deleting existing DebugLevel objects')
        result = self.task.tooling.query('Select Id from DebugLevel')
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
