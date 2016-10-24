import base64
import logging
import os
import tempfile
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
        raise NotImplementedError('Subclasses should provide their own implementation')

    def _refresh_oauth_token(self):
        self.org_config.refresh_oauth_token(self.project_config.keychain.get_connected_app())

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

class BaseSalesforceToolingApiTask(BaseSalesforceTask):
    api_class = None
    name = 'BaseSalesforceToolingApiTask'

    def _init_task(self):
        self.tooling = Salesforce(
            instance=self.org_config.instance_url,
            session_id=self.org_config.access_token,
            version=self.project_config.project__api_version,
        )
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

        self.logger.info('Deploying all metadata bundles in path {}'.format(path))

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
