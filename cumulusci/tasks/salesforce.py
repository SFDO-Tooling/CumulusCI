import base64
import logging
import os
import tempfile
import zipfile

from simple_salesforce import Salesforce

from cumulusci.core.tasks import BaseTask
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.metadata import ApiRetrieveInstalledPackages
from cumulusci.salesforce_api.metadata import ApiRetrievePackaged
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.salesforce_api.package_zip import CreatePackageZipBuilder
from cumulusci.salesforce_api.package_zip import DestructiveChangesZipBuilder
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.salesforce_api.package_zip import UninstallPackageZipBuilder
from cumulusci.utils import zip_subfolder

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

class BaseRetrieveMetadata(BaseSalesforceMetadataApiTask):
    task_options = {
        'path': {
            'description': 'The path to write the retrieved metadata',
            'required': True,
        }
    }

    def _run_task(self):
        api = self._get_api()
        src_zip = api()
        self._extract_zip(src_zip)
        self.logger.info('Extracted retrieved metadata into {}'.format(self.options['path']))

    def _extract_zip(self, src_zip):
        src_zip.extractall(self.options['path'])


class RetrieveUnpackaged(BaseRetrieveMetadata):
    api_class = ApiRetrieveUnpackaged

    task_options = {
        'path': {
            'description': 'The path where the retrieved metadata should be written',
            'required': True,
        },
        'package_xml': {
            'description': 'The package.xml manifest to use for the retrieve.',
            'required': True,
        },
        'api_version': {
            'description': 'Override the default api version for the retrieve.  Defaults to project__package__api_version',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(RetrieveUnpackaged, self)._init_options(kwargs)

        if 'api_version' not in self.options:
            self.options['api_version'] = self.project_config.project__package__api_version

        if 'package_xml' in self.options:
            self.options['package_xml_path'] = self.options['package_xml']
            self.options['package_xml'] = open(self.options['package_xml_path'], 'r').read()

    def _get_api(self):
        return self.api_class(
            self,
            self.options['package_xml'],
            self.options['api_version'],
        )
   
 
class RetrievePackaged(BaseRetrieveMetadata):
    api_class = ApiRetrievePackaged

    task_options = {
        'path': {
            'description': 'The path where the retrieved metadata should be written',
            'required': True,
        },
        'package': {
            'description': 'The package name to retrieve.  Defaults to project__package__name',
            'required': True,
        },
        'api_version': {
            'description': 'Override the default api version for the retrieve.  Defaults to project__package__api_version',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(RetrievePackaged, self)._init_options(kwargs)
        if 'package' not in self.options:
            self.options['package'] = self.project_config.project__package__name
        if 'api_version' not in self.options:
            self.options['api_version'] = self.project_config.project__package__api_version

    def _get_api(self):
        return self.api_class(
            self,
            self.options['package'],
            self.options['api_version'],
        )

    def _extract_zip(self, src_zip):
        src_zip = zip_subfolder(src_zip, self.options.get('package')) 
        super(RetrievePackaged, self)._extract_zip(src_zip)

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
                self._write_zip_file(zipf, root, f)
        zipf.close()
        zip_file.seek(0)
        package_zip = base64.b64encode(zip_file.read())

        os.chdir(pwd)

        return self.api_class(self, package_zip)

    def _write_zip_file(self, zipf, root, path):
        zipf.write(os.path.join(root, path))
       

class CreatePackage(Deploy):
    task_options = {
        'package': {
            'description': 'The name of the package to create.  Defaults to project__package__name',
            'required': True,
        },
        'api_version': {
            'description': 'The api version to use when creating the package.  Defaults to project__package__api_version',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(CreatePackage, self)._init_options(kwargs)
        if 'package' not in self.options:
            self.options['package'] = self.project_config.project__package__name
        if 'api_version' not in self.options:
            self.options['api_version'] = self.project_config.project__package__api_version

    def _get_api(self, path=None):
        package_zip = CreatePackageZipBuilder(self.options['package'], self.options['api_version'])
        return self.api_class(self, package_zip())

class InstallPackageVersion(Deploy):
    task_options = {
        'namespace': {
            'description': 'The namespace of the package to install.  Defaults to project__package__namespace',
            'required': True,
        },
        'version': {
            'description': 'The version of the package to install',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(InstallPackageVersion, self)._init_options(kwargs)
        if 'namespace' not in self.options:
            self.options['namespace'] = self.project_config.project__package__namespace

    def _get_api(self, path=None):
        package_zip = InstallPackageZipBuilder(self.options['namespace'], self.options['version'])
        return self.api_class(self, package_zip())

class UninstallPackage(Deploy):
    task_options = {
        'namespace': {
            'description': 'The namespace of the package to uninstall.  Defaults to project__package__namespace',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(UninstallPackage, self)._init_options(kwargs)
        if 'namespace' not in self.options:
            self.options['namespace'] = self.project_config.project__package__namespace

    def _get_api(self, path=None):
        package_zip = UninstallPackageZipBuilder(self.options['namespace'])
        return self.api_class(self, package_zip())

class DeployBundles(Deploy):
    task_options = {
        'path': {
            'description': 'The path to the parent directory containing the metadata bundles directories',
            'required': True,
        }
    }

    def _run_task(self):
        path = self.options['path']
        pwd = os.getcwd()

        path = os.path.join(pwd, path)

        self.logger.info('Deploying all metadata bundles in path {}'.format(path))

        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if not os.path.isdir(item_path):
                continue

            self.logger.info('Deploying bundle: {}/{}'.format(self.options['path'], item))

            self._deploy_bundle(item_path)

    def _deploy_bundle(self, path):
        api = self._get_api(path)
        return api()

class DeployNamespacedBundles(DeployBundles):
    name = 'DeployNamespacedBundles'

    task_options = {
        'path': {
            'description': 'The path to the parent directory containing the metadata bundles directories',
            'required': True,
        },
        'managed': {
            'description': 'If True, will insert the actual namespace prefix.  Defaults to False or no namespace',
        },
        'namespace': {
            'description': 'The namespace to replace the token with if in managed mode. Defaults to project__package__namespace',
        },
        'namespace_token': {
            'description': 'The string token to replace with the namespace',
            'required': True,
        },
        'filename_token': {
            'description': 'The path to the parent directory containing the metadata bundles directories',
            'required': True,
        },
    }
    
    def _init_options(self, kwargs):
        super(DeployNamespacedBundles, self)._init_options(kwargs)

        if 'managed' not in self.options:
            self.options['managed'] = False

        if 'namespace' not in self.options:
            self.options['namespace'] = self.project_config.project__package__namespace

    def _write_zip_file(self, zipf, root, path):
        if self.options['managed'] in [True, 'True', 'true']:
            namespace = self.options['namespace']
            if namespace:
                namespace = namespace + '__'
        else:
            namespace = ''

        path = path.replace(self.options['filename_token'], namespace)
        content = open(os.path.join(root, path), 'r').read()
        content = content.replace(self.options['namespace_token'], namespace)
        zipf.writestr(path, content)

class BaseUninstallMetadata(Deploy):

    def _get_api(self, path=None):
        destructive_changes = self._get_destructive_changes(path=path)
        package_zip = DestructiveChangesZipBuilder(destructive_changes) 
        api = self.api_class(self, package_zip())
        return api


class UninstallLocal(BaseUninstallMetadata):
    
    def _get_destructive_changes(self, path=None):
        if not path:
            path = self.options['path']

        generator = PackageXmlGenerator(
            directory = path,
            api_version = self.project_config.project__package__api_version,
            delete = True,
        )
        return generator()

class UninstallPackaged(UninstallLocal):

    task_options = {
        'package': {
            'description': 'The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(UninstallPackaged, self)._init_options(kwargs)
        if 'package' not in self.options:
            self.options['package'] = self.project_config.project__package__name

    def _get_destructive_changes(self, path=None):
        self.logger.info('Retrieving metadata in package {} from target org'.format(self.options['package']))
        retrieve_api = ApiRetrievePackaged(self, self.options['package'])
        packaged = retrieve_api()

        tempdir = tempfile.mkdtemp()
        packaged.extractall(tempdir)

        destructive_changes = super(UninstallPackaged, self)._get_destructive_changes(
            os.path.join(tempdir, self.options['package'])
        )

        self.logger.info('Deleting metadata in package {} from target org'.format(self.options['package']))
        return destructive_changes

class UninstallLocalBundles(UninstallLocal):

    def _run_task(self):
        path = self.options['path']
        pwd = os.getcwd()

        path = os.path.join(pwd, path)

        self.logger.info('Deleting all metadata from bundles in {} from target org'.format(path))

        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if not os.path.isdir(item_path):
                continue

            self.logger.info('Deleting bundle: {}/{}'.format(self.options['path'], item))

            self._delete_bundle(item_path)

    def _delete_bundle(self, path=None):
        api = self._get_api(path)
        return api()

class UninstallLocalNamespacedBundles(UninstallLocalBundles):

    task_options = {
        'path': {
            'description': 'The path to a directory containing the metadata bundles (subdirectories) to uninstall',
            'required': True,
        },
        'managed': {
            'description': 'If True, will insert the actual namespace prefix.  Defaults to False or no namespace',
        },
        'namespace': {
            'description': 'The namespace to replace the token with if in managed mode. Defaults to project__package__namespace',
        },
        'filename_token': {
            'description': 'The path to the parent directory containing the metadata bundles directories',
            'required': True,
        },
    }
    
    def _init_options(self, kwargs):
        super(UninstallLocalNamespacedBundles, self)._init_options(kwargs)

        if 'managed' not in self.options:
            self.options['managed'] = False

        if 'namespace' not in self.options:
            self.options['namespace'] = self.project_config.project__package__namespace

    def _get_destructive_changes(self, path=None):
        if not path:
            path = self.options['path']

        generator = PackageXmlGenerator(
            directory = path,
            api_version = self.project_config.project__package__api_version,
            delete = True,
        )
        namespace = ''
        if self.options['managed'] in [True, 'True', 'true']:
            if self.options['namespace']:
                namespace = self.options['namespace'] + '__'

        destructive_changes = generator()
        destructive_changes.replace(self.options['filename_token'], namespace)

        return destructive_changes

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
            self.options['package_xml'] = os.path.join(CUMULUSCI_PATH, 'build', 'admin_profile.xml')

        self.options['package_xml_path'] = self.options['package_xml']
        self.options['package_xml'] = open(self.options['package_xml_path'], 'r').read()

    def _run_task(self):
        self.tempdir = tempfile.mkdtemp()
        self._retrieve_unpackaged()
        self._process_metadata()
        self._deploy_metadata()

    def _retrieve_unpackaged(self):
        self.logger.info('Retrieving metadata using {}'.format(self.options['package_xml_path']))
        api_retrieve = ApiRetrieveUnpackaged(
            self,
            self.options.get('package_xml'),
            self.project_config.project__package__api_version,
        )
        unpackaged = api_retrieve()
        unpackaged.extractall(self.tempdir)

    def _process_unpackaged(self):
        self.logger.info('Processing retrieved metadata in {}'.format(self.tempdir))

        findReplaceRegex(
            '<editable>false</editable>',
            '<editable>true</editable>',
            os.path.join(self.tempdir, 'profiles'),
            'Admin.profile',
        )


class PackageUpload(BaseSalesforceToolingApiTask):
    name = 'PackageUpload'
    task_options = {
        'name': {
            'description': 'The name of the package version.',
            'required': True,
        },
        'production': {
            'description': 'If True, uploads a production release.  Defaults to uploading a beta',
        },
        'description': {
            'description': 'A description of the package and what this version contains.',
        },
        'password': {
            'description': "An optional password for sharing the package privately with anyone who has the password. Don't enter a password if you want to make the package available to anyone on AppExchange and share your package publicly.",
        },
        'post_install_url': {
            'description': 'The fully-qualified URL of the post-installation instructions. Instructions are shown as a link after installation and are available from the package detail view.',
        },
        'release_notes_url': {
            'description': 'The fully-qualified URL of the package release notes. Release notes are shown as a link during the installation process and are available from the package detail view after installation.',
        },
        'namespace': {
            'description': 'The namespace of the package.  Defaults to project__package__namespace',
        },
    }

    def _init_options(self, kwargs):
        super(PackageUpload, self)._init_options(kwargs)

        # Set the namespace option to the value from cumulusci.yml if not already set
        if not 'namespace' in self.options:
            self.options['namespace'] = self.project_config.project__package__namespace

    def _run_task(self):
        sf = self._init_api()
        package_res = sf.query("select Id from MetadataPackage where NamespacePrefix=''".format(self.options['namespace']))

        production = self.options.get('production', False) in [True, 'True', 'true']
        package_info = {
            'VersionName': self.options['name'],
            'IsReleaseVersion': production,
        }
        
        if 'description' in self.options:
            package_info['Description'] = self.options['description']
        if 'password' in self.options:
            package_info['Password'] = self.options['password']
        if 'post_install_url' in self.options:
            package_info['PostInstallUrl'] = self.options['post_install_url']
        if 'release_notes_url' in self.options:
            package_info['ReleaseNotesUrl'] = self.options['release_notes_url']

        upload = self.tooling.PackageUploadRequest.create(package_info)[0]

        while upload.status == 'InProgress':
            time.sleep(3)
            upload = self.tooling.query("select Status, Errors from PackageUploadRequest where Id = '{}'".format(upload['Id']))[0]

        self.logger.info('Uploaded package version: {}'.format(str(upload)))
