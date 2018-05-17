import os
import shutil
import tempfile

from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.salesforce import Deploy
from cumulusci.utils import CUMULUSCI_PATH
from cumulusci.utils import findReplace


class UpdateAdminProfile(Deploy):
    name = 'UpdateAdminProfile'

    task_options = {
        'package_xml': {
            'description': 'Override the default package.xml file for retrieving the Admin.profile and all objects and classes that need to be included by providing a path to your custom package.xml',
        }
    }

    def _init_options(self, kwargs):
        super(UpdateAdminProfile, self)._init_options(kwargs)

        if 'package_xml' not in self.options:
            self.options['package_xml'] = os.path.join(CUMULUSCI_PATH, 'cumulusci', 'files', 'admin_profile.xml')

        self.options['package_xml_path'] = self.options['package_xml']
        with open(self.options['package_xml_path'], 'r') as f:
            self.options['package_xml'] = f.read()

    def _run_task(self):
        self.tempdir = tempfile.mkdtemp()
        self._retrieve_unpackaged()
        self._process_metadata()
        self._deploy_metadata()
        shutil.rmtree(self.tempdir)

    def _retrieve_unpackaged(self):
        self.logger.info('Retrieving metadata using {}'.format(self.options['package_xml_path']))
        api_retrieve = ApiRetrieveUnpackaged(
            self,
            self.options.get('package_xml'),
            self.project_config.project__package__api_version,
        )
        unpackaged = api_retrieve()
        unpackaged.extractall(self.tempdir)

    def _process_metadata(self):
        self.logger.info('Processing retrieved metadata in {}'.format(self.tempdir))

        findReplace(
            '<editable>false</editable>',
            '<editable>true</editable>',
            os.path.join(self.tempdir, 'profiles'),
            'Admin.profile',
        )
        findReplace(
            '<readable>false</readable>',
            '<readable>true</readable>',
            os.path.join(self.tempdir, 'profiles'),
            'Admin.profile',
        )

    def _deploy_metadata(self):
        self.logger.info('Deploying updated Admin.profile from {}'.format(self.tempdir))
        api = self._get_api(path=self.tempdir)
        return api()
