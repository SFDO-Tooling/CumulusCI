from datetime import datetime
import json
import re

from cumulusci.core.utils import process_bool_arg
from cumulusci.core.utils import parse_datetime
from cumulusci.tasks.github.base import BaseGithubTask


class ReleaseReport(BaseGithubTask):
    task_options = {
        'date_start': {
            'description': 'Filter out releases created before this date (YYYY-MM-DD)',
        },
        'date_end': {
            'description': 'Filter out releases created after this date (YYYY-MM-DD)',
        },
        'include_beta': {
            'description': 'Include beta releases in report [default=False]',
        },
        'print': {
            'description': 'Print info to screen as JSON [default=False]',
        },
    }
    DATE_FORMAT = '%Y-%m-%d'

    def _init_options(self, kwargs):
        super(ReleaseReport, self)._init_options(kwargs)
        self.options['date_start'] = parse_datetime(
            self.options['date_start'],
            self.DATE_FORMAT,
        ) if 'date_start' in self.options else None
        self.options['date_end'] = parse_datetime(
            self.options['date_end'],
            self.DATE_FORMAT,
        ) if 'date_end' in self.options else None
        self.options['include_beta'] = process_bool_arg(
            self.options.get('include_beta', False))
        self.options['print'] = process_bool_arg(
            self.options.get('print', False))

    def _run_task(self):
        releases = []
        last_time = None
        repo = self.get_repo()
        regex_compiled = re.compile(
            r'^((?P<sandbox>{})|(?P<production>{}))\s*(?P<date>\d\d\d\d-\d\d-\d\d)'.format(
                self.project_config.project__git__push_prefix_sandbox,
                self.project_config.project__git__push_prefix_production,
            ))
        for release in repo.iter_releases():
            if release.prerelease and not self.options['include_beta']:
                continue
            if self.options['date_start'] and release.created_at < self.options[
                    'date_start']:
                continue
            if self.options[
                    'date_end'] and release.created_at > self.options['date_end']:
                continue
            release_info = {
                'url': release.html_url,
                'name': release.name,
                'tag': release.tag_name,
                'beta': release.prerelease,
                'time_created': release.created_at,
                'time_push_sandbox': None,
                'time_push_production': None,
            }
            for line in release.body.splitlines():
                m = regex_compiled.match(line)
                if m:
                    if m.group('sandbox'):
                        key = 'time_push_sandbox'
                    else:
                        key = 'time_push_production'
                    release_info[key] = parse_datetime(
                        m.group('date'),
                        self.DATE_FORMAT,
                    )
            releases.append(release_info)
        self.return_values = {'releases': releases}
        if self.options['print']:
            print(json.dumps(releases, indent=4, sort_keys=True, default=str))
