import httplib
import json

import requests

from cumulusci.core.exceptions import MrbelvedereError
from cumulusci.core.tasks import BaseTask


class BaseMrbelvedereTask(BaseTask):

    def _init_task(self):
        self.mrbelvedere_config = self.project_config.keychain.get_service(
            'mrbelvedere')


class MrbelvederePublish(BaseMrbelvedereTask):

    task_options = {
        'tag': {
            'description': 'The tag to publish to mrbelvedere',
            'required': True,
        },
    }

    def _init_task(self):
        super(MrbelvederePublish, self)._init_task()
        self.dependencies_url = '{}/{}/dependencies'.format(
            self.mrbelvedere_config.base_url,
            self.project_config.project__package__namespace,
        )
        if self.options['tag'].startswith(
                self.project_config.project__git__prefix_beta):
            self.dependencies_url += '/beta'
        self.current_dependencies = []

    def _run_task(self):
        self._get_current_dependencies()
        diffs = self._get_diffs()
        if diffs:
            response = requests.post(
                self.dependencies_url,
                data=json.dumps(diffs),
                headers={'Authorization': self.mrbelvedere_config.api_key},
            )
            if response.status_code >= httplib.BAD_REQUEST:
                raise MrbelvedereError('{}: {}'.format(
                    response.status_code, response.content))
            self.logger.info(response.content)

    def _get_current_dependencies(self):
        response = requests.get(self.dependencies_url)
        self.current_dependencies = json.loads(response.content)

    def _get_diffs(self):
        # flatten dependency tree, resolve duplicates
        dependencies = self._clean_dependencies(
            self.project_config.get_static_dependencies())
        # determine diffs vs current dependencies
        diffs = []
        for current_dependency in self.current_dependencies:
            match = False
            for dependency in dependencies:
                if dependency['namespace'] == current_dependency['namespace']:
                    match = True
                    if dependency['number'] == current_dependency['number']:
                        self.logger.info('No change for %s',
                                         current_dependency['namespace'])
                    else:
                        self.logger.info('Changing %s from version %s to %g',
                            dependency['namespace'],
                            current_dependency['number'],
                            dependency['number'],
                        )
                        diffs.append(dependency)
                    break
            if not match:
                self.logger.info('No change for %s',
                                 current_dependency['namespace'])
        diffs.append({
            'namespace': self.project_config.project__package__namespace,
            'number': self.project_config.get_version_for_tag(
                self.options['tag']),
        })
        return diffs

    def _clean_dependencies(self, dependency_list):
        cleaned_dependencies = []
        if not dependency_list:
            return cleaned_dependencies
        for dependency in dependency_list:
            if 'namespace' not in dependency:
                continue
            if 'dependencies' in dependency:
                cleaned_dependencies.extend(
                    self._clean_dependencies(dependency['dependencies']))
            # update version
            exists = False
            for item in cleaned_dependencies:
                if item['namespace'] == dependency['namespace']:
                    exists = True
                    if item['number'] < dependency['version']:
                        item['number'] = str(dependency['version'])
                    break
            # add new entry
            if not exists:
                cleaned_dependencies.append({
                    'namespace': dependency['namespace'],
                    'number': str(dependency['version']),
                })
        return cleaned_dependencies
