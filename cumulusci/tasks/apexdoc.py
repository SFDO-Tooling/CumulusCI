import os
import tempfile
import urllib

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.command import Command


class GenerateApexDocs(Command):
    """ Generate Apex documentation from local code """
    apexdoc_repo_url = 'https://github.com/SalesforceFoundation/ApexDoc'
    jar_file = 'apexdoc.jar'
    task_options = {
        'tag': {
            'description': 'The tag to use for links back to repo.',
            'required': True,
        },
        'out_dir': {
            'description': 'Directory to write Apex docs. ApexDoc tool will ' +
            'write files to a subdirectory called ApexDocumentation which ' +
            'will be created if it does not exist. default=repo_root',
        },
    }
    
    def _init_options(self, kwargs):
        super(GenerateApexDocs, self)._init_options(kwargs)
        self.options['command'] = None
        if 'out_dir' not in self.options:
            self.options['out_dir'] = (
                self.project_config.project__apexdoc__dir
                if self.project_config.project__apexdoc__dir
                else self.project_config.repo_root
            )

    def _init_task(self):
        super(GenerateApexDocs, self)._init_task()
        self.working_dir = tempfile.mkdtemp()
        self.jar_path = os.path.join(self.working_dir, self.jar_file)
        if not self.project_config.project__git__repo_url:
            raise CumulusCIException('Repo URL not found in cumulusci.yml')
        self.source_url = '{}/blob/{}/src/classes/'.format(
            self.project_config.project__git__repo_url,
            self.options['tag'],
        )

    def _run_task(self):
        self._get_jar()
        self.options['command'] = ('java ' +
            '-jar {} -s {} -t {} -g {} -h {} -a {} -p "{}"'.format(
                self.jar_path,
                os.path.join(self.project_config.repo_root, 'src', 'classes'),
                self.options['out_dir'],
                self.source_url,
                self.project_config.project__apexdoc__homepage,
                self.project_config.project__apexdoc__banner,
                self.project_config.project__apexdoc__scope,
            )
        )
        self._run_command({})

    def _get_jar(self):
        url = '{}/releases/download/{}/{}'.format(
            self.apexdoc_repo_url,
            self.project_config.project__apexdoc['version'],
            self.jar_file,
        )
        urllib.urlretrieve(url, self.jar_path)
