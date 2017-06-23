import base64
import cgi
import datetime
from distutils.version import LooseVersion
import errno
import io
import json
import logging
import os
import re
import shutil
import tempfile
import time
import zipfile

import hiyapyco
from github3.repos.repo import Release
from simple_salesforce import Salesforce
from simple_salesforce import SalesforceGeneralError
from salesforce_bulk import SalesforceBulk
import xmltodict

from cumulusci.core.exceptions import ApexTestException
from cumulusci.core.exceptions import SalesforceException
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseTask
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.metadata import ApiListMetadata
from cumulusci.salesforce_api.metadata import ApiRetrieveInstalledPackages
from cumulusci.salesforce_api.metadata import ApiRetrievePackaged
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.salesforce_api.package_zip import CreatePackageZipBuilder
from cumulusci.salesforce_api.package_zip import DestructiveChangesZipBuilder
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.salesforce_api.package_zip import UninstallPackageZipBuilder
from cumulusci.salesforce_api.package_zip import ZipfilePackageZipBuilder
from cumulusci.utils import CUMULUSCI_PATH
from cumulusci.utils import download_extract_zip
from cumulusci.utils import findReplace
from cumulusci.utils import package_xml_from_dict
from cumulusci.utils import zip_inject_namespace
from cumulusci.utils import zip_strip_namespace
from cumulusci.utils import zip_tokenize_namespace
from cumulusci.utils import zip_subfolder


class BaseSalesforceTask(BaseTask):
    name = 'BaseSalesforceTask'
    salesforce_task = True

    def _run_task(self):
        raise NotImplementedError(
            'Subclasses should provide their own implementation')

    def _update_credentials(self):
        self.org_config.refresh_oauth_token(self.project_config.keychain.get_connected_app())


class BaseSalesforceMetadataApiTask(BaseSalesforceTask):
    api_class = None
    name = 'BaseSalesforceMetadataApiTask'

    def _get_api(self):
        return self.api_class(self)

    def _run_task(self):
        api = self._get_api()
        if api:
            return api()


class BaseSalesforceApiTask(BaseSalesforceTask):
    name = 'BaseSalesforceApiTask'
    api_version = None

    def _init_task(self):
        self.sf = self._init_api()
        self.bulk = self._init_bulk()
        self.tooling = self._init_api('tooling/')
        self._init_class()
    

    def _init_api(self, base_url=None):
        if self.api_version:
            api_version = self.api_version
        else:
            api_version = self.project_config.project__package__api_version

        rv = Salesforce(
            instance=self.org_config.instance_url.replace('https://', ''),
            session_id=self.org_config.access_token,
            version=api_version,
        )
        if base_url is not None:
            rv.base_url += base_url
        return rv

    def _init_bulk(self):
        return SalesforceBulk(
            host=self.org_config.instance_url.replace('https://', ''),
            sessionId=self.org_config.access_token,
        )

    def _init_class(self):
        pass

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
        },
        'unmanaged': {
            'description': "If True, changes namespace_inject to replace tokens with a blank string",
        },
        'namespace_inject': {
            'description': "If set, the namespace tokens in files and filenames are replaced with the namespace's prefix",
        },
        'namespace_strip': {
            'description': "If set, all namespace prefixes for the namespace specified are stripped from files and filenames",
        },
        'namespace_tokenize': {
            'description': "If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject",
        },
    }

    def _run_task(self):
        api = self._get_api()
        src_zip = api()
        self._extract_zip(src_zip)
        self.logger.info('Extracted retrieved metadata into {}'.format(self.options['path']))

    def _process_namespace(self, src_zip):
        if self.options.get('namespace_tokenize'):
            src_zip = zip_tokenize_namespace(src_zip, self.options['namespace_tokenize'])
        if self.options.get('namespace_inject'):
            if self.options.get('unmanaged'):
                src_zip = zip_inject_namespace(src_zip, self.options['namespace_inject'])
            else:
                src_zip = zip_inject_namespace(src_zip, self.options['namespace_inject'], True)
        if self.options.get('namespace_strip'):
            src_zip = zip_strip_namespace(src_zip, self.options['namespace_strip'])
        return src_zip

    def _extract_zip(self, src_zip):
        src_zip = self._process_namespace(src_zip)
        src_zip.extractall(self.options['path'])


retrieve_unpackaged_options = BaseRetrieveMetadata.task_options.copy()
retrieve_unpackaged_options.update({
    'package_xml': {
        'description': 'The path to a package.xml manifest to use for the retrieve.',
        'required': True,
    },
    'api_version': {
        'description': (
            'Override the default api version for the retrieve.' +
            ' Defaults to project__package__api_version'
        ),
    },
})
class RetrieveUnpackaged(BaseRetrieveMetadata):
    api_class = ApiRetrieveUnpackaged

    task_options = retrieve_unpackaged_options

    def _init_options(self, kwargs):
        super(RetrieveUnpackaged, self)._init_options(kwargs)

        if 'package_xml' in self.options:
            self.options['package_xml_path'] = self.options['package_xml']
            with open(self.options['package_xml_path'], 'r') as f:
                self.options['package_xml'] = f.read()

    def _get_api(self):
        return self.api_class(
            self,
            self.options['package_xml'],
            self.options.get('api_version'),
        )

retrieve_packaged_options = BaseRetrieveMetadata.task_options.copy()
retrieve_packaged_options.update({
    'package': {
        'description': 'The package name to retrieve.  Defaults to project__package__name',
        'required': True,
    },
    'api_version': {
        'description': (
            'Override the default api version for the retrieve.' +
            ' Defaults to project__package__api_version'
        ),
    },
})

class RetrievePackaged(BaseRetrieveMetadata):
    api_class = ApiRetrievePackaged

    task_options = retrieve_packaged_options

    def _init_options(self, kwargs):
        super(RetrievePackaged, self)._init_options(kwargs)
        if 'package' not in self.options:
            self.options['package'] = self.project_config.project__package__name

    def _get_api(self):
        return self.api_class(
            self,
            self.options['package'],
            self.options.get('api_version'),
        )

    def _extract_zip(self, src_zip):
        src_zip = zip_subfolder(src_zip, self.options.get('package'))
        super(RetrievePackaged, self)._extract_zip(src_zip)


retrieve_reportsanddashboards_options = BaseRetrieveMetadata.task_options.copy()
retrieve_reportsanddashboards_options.update({
    'report_folders': {
        'description': 'A list of the report folders to retrieve reports.  Separate by commas for multiple folders.',
    },
    'dashboard_folders': {
        'description': 'A list of the dashboard folders to retrieve reports.  Separate by commas for multiple folders.',
    },
    'api_version': {
        'description': 'Override the API version used to list metadata',
    }
})

class RetrieveReportsAndDashboards(BaseRetrieveMetadata):
    api_class = ApiRetrieveUnpackaged

    task_options = retrieve_reportsanddashboards_options

    def _init_options(self, kwargs):
        super(RetrieveReportsAndDashboards, self)._init_options(kwargs)
        if 'api_version' not in self.options:
            self.options['api_version'] = (
                self.project_config.project__package__api_version
            )

    def _validate_options(self):
        super(RetrieveReportsAndDashboards, self)._validate_options()
        if not 'report_folders' in self.options and not 'dashboard_folders' in self.options:
            raise TaskOptionsError('You must provide at least one folder name for either report_folders or dashboard_folders')

    def _get_api(self):
        metadata = {}
        if 'report_folders' in self.options:
            for folder in self.options['report_folders']:
                api_reports = ApiListMetadata(
                    self,
                    'Report',
                    metadata=metadata,
                    folder=folder,
                    as_of_version=self.options['api_version'],
                )
                metadata = api_reports()
        if 'dashboard_folders' in self.options:
            for folder in self.options['dashboard_folders']:
                api_dashboards = ApiListMetadata(
                    self,
                    'Dashboard',
                    metadata=metadata,
                    folder=folder,
                    as_of_version=self.options['api_version'],
                )
                metadata = api_dashboards()

        items = {}
        if 'Report' in metadata:
            items['Report'] = []
            items['Report'].extend(self.options['report_folders'])
            for report in metadata['Report']:
                items['Report'].append(report['fullName'])
        if 'Dashboard' in metadata:
            items['Dashboard'] = []
            items['Dashboard'].extend(self.options['dashboard_folders'])
            for dashboard in metadata['Dashboard']:
                items['Dashboard'].append(dashboard['fullName'])

        api_version = self.project_config.project__package__api_version
        package_xml = package_xml_from_dict(items, api_version)
        print package_xml
        return self.api_class(
            self,
            package_xml,
            api_version,
        )

class Deploy(BaseSalesforceMetadataApiTask):
    api_class = ApiDeploy
    task_options = {
        'path': {
            'description': 'The path to the metadata source to be deployed',
            'required': True,
        },
        'unmanaged': {
            'description': "If True, changes namespace_inject to replace tokens with a blank string",
        },
        'namespace_inject': {
            'description': "If set, the namespace tokens in files and filenames are replaced with the namespace's prefix",
        },
        'namespace_strip': {
            'description': "If set, all namespace prefixes for the namespace specified are stripped from files and filenames",
        },
        'namespace_tokenize': {
            'description': "If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject",
        },
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
        zipf = self._process_zip_file(zipf)
        zipf.fp.seek(0)
        package_zip = base64.b64encode(zipf.fp.read())

        os.chdir(pwd)

        return self.api_class(self, package_zip, purge_on_delete=False)

    def _process_zip_file(self, zipf):
        zipf = self._process_namespace(zipf)
        return zipf
        
    def _process_namespace(self, zipf):
        if self.options.get('namespace_tokenize'):
            self.logger.info(
                'Tokenizing namespace prefix {}__'.format(
                    self.options['namespace_tokenize'],
                )
            )
            zipf = zip_tokenize_namespace(zipf, self.options['namespace_tokenize'])
        if self.options.get('namespace_inject'):
            if self.options.get('unmanaged'):
                self.logger.info(
                    'Stripping namespace tokens from metadata for unmanaged deployment'
                )
                zipf = zip_inject_namespace(zipf, self.options['namespace_inject'])
            else:
                self.logger.info(
                    'Replacing namespace tokens from metadata with namespace prefix {}__'.format(
                        self.options['namespace_inject'],
                    )
                )
                zipf = zip_inject_namespace(zipf, self.options['namespace_inject'], True)
        if self.options.get('namespace_strip'):
            zipf = zip_strip_namespace(zipf, self.options['namespace_strip'])
        return zipf

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
        return self.api_class(self, package_zip(), purge_on_delete=False)

class InstallPackageVersion(Deploy):
    task_options = {
        'namespace': {
            'description': 'The namespace of the package to install.  Defaults to project__package__namespace',
            'required': True,
        },
        'version': {
            'description': 'The version of the package to install.  "latest" and "latest_beta" can be used to trigger lookup via Github Releases on the repository.',
            'required': True,
        },
        'retries': {
            'description': 'Number of retries (default=5)',
        },
        'retry_interval': {
            'description': 'Number of seconds to wait before the next retry (default=5),'
        },
        'retry_interval_add': {
            'description': 'Number of seconds to add before each retry (default=30),'
        },
    }

    def _init_options(self, kwargs):
        super(InstallPackageVersion, self)._init_options(kwargs)
        if 'namespace' not in self.options:
            self.options['namespace'] = self.project_config.project__package__namespace
        if 'retries' not in self.options:
            self.options['retries'] = 5
        if 'retry_interval' not in self.options:
            self.options['retry_interval'] = 5
        if 'retry_interval_add' not in self.options:
            self.options['retry_interval_add'] = 30
        if self.options.get('version') == 'latest':
            self.options['version'] = self.project_config.get_latest_version()
            self.logger.info('Installing latest release: {}'.format(self.options['version']))
        elif self.options.get('version') == 'latest_beta':
            self.options['version'] = self.project_config.get_latest_version(beta=True)
            self.logger.info('Installing latest beta release: {}'.format(self.options['version']))

    def _get_api(self, path=None):
        package_zip = InstallPackageZipBuilder(self.options['namespace'], self.options['version'])
        return self.api_class(self, package_zip(), purge_on_delete=False)

    def _run_task(self):
        self._retry()

    def _try(self):
        api = self._get_api()
        api()

    def _is_retry_valid(self, e):
        if (isinstance(e, MetadataApiError) and
            ('This package is not yet available' in e.message or
            'InstalledPackage version number' in e.message)):
            return True

class UninstallPackage(Deploy):
    task_options = {
        'namespace': {
            'description': 'The namespace of the package to uninstall.  Defaults to project__package__namespace',
            'required': True,
        },
        'purge_on_delete': {
            'description': 'Sets the purgeOnDelete option for the deployment.  Defaults to True',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(UninstallPackage, self)._init_options(kwargs)
        if 'namespace' not in self.options:
            self.options['namespace'] = self.project_config.project__package__namespace
        if 'purge_on_delete' not in self.options:
            self.options['purge_on_delete'] = True
        if self.options['purge_on_delete'] == 'False':
            self.options['purge_on_delete'] = False

    def _get_api(self, path=None):
        package_zip = UninstallPackageZipBuilder(
            self.options['namespace'],
            self.project_config.project__package__api_version,
        )
        return self.api_class(self, package_zip(), purge_on_delete=self.options['purge_on_delete'])

class UpdateDependencies(BaseSalesforceMetadataApiTask):
    api_class = ApiDeploy
    name = 'UpdateDependencies'
    task_options = {
        'purge_on_delete': {
            'description': 'Sets the purgeOnDelete option for the deployment. Defaults to True',
        },
    }

    def _init_options(self, kwargs):
        super(UpdateDependencies, self)._init_options(kwargs)
        if 'purge_on_delete' not in self.options:
            self.options['purge_on_delete'] = True
        if (isinstance(self.options['purge_on_delete'], basestring) and
            self.options['purge_on_delete'].lower() == 'false'):
            self.options['purge_on_delete'] = False

    def _run_task(self):
        if not self.project_config.project__dependencies:
            self.logger.info('Project has no dependencies, doing nothing')
            return

        self.logger.info('Preparing static dependencies map')
        dependencies = self.project_config.get_static_dependencies()

        self.installed = self._get_installed()
        self.uninstall_queue = []
        self.install_queue = []

        self.logger.info('Dependencies:')
        for line in self.project_config.pretty_dependencies(dependencies):
            self.logger.info(line)

        self._process_dependencies(dependencies)

        # Reverse the uninstall queue
        self.uninstall_queue.reverse()

        self._uninstall_dependencies()
        self._install_dependencies()

    def _process_dependencies(self, dependencies):
        for dependency in dependencies:
            # Process child dependencies
            dependency_uninstalled = False
            if 'dependencies' in dependency and dependency['dependencies']:
                count_uninstall = len(self.uninstall_queue)
                self._process_dependencies(dependency['dependencies'])
                if count_uninstall != len(self.uninstall_queue):
                    dependency_uninstalled = True

            # Process zip_url dependencies (unmanaged metadata)
            if 'zip_url' in dependency:
                self._process_zip_dependency(dependency)

            # Process namespace dependencies (managed packages)
            elif 'namespace' in dependency:
                self._process_namespace_dependency(dependency, dependency_uninstalled)

    def _process_zip_dependency(self, dependency):
        self.install_queue.append(dependency)    

    def _process_namespace_dependency(self, dependency, dependency_uninstalled=None):
        dependency_version = str(dependency['version'])

        if dependency['namespace'] in self.installed:
            # Some version is installed, check what to do
            installed_version = self.installed[dependency['namespace']]
            if dependency_version == installed_version:
                self.logger.info('  {}: version {} already installed'.format(
                    dependency['namespace'],
                    dependency_version,
                ))
                return

            required_version = LooseVersion(dependency_version)
            installed_version = LooseVersion(installed_version)

            if 'Beta' in installed_version.vstring:
                # Always uninstall Beta versions if required is different
                self.uninstall_queue.append(dependency)
                self.logger.info('  {}: Uninstall {} to upgrade to {}'.format(
                    dependency['namespace'],
                    installed_version,
                    dependency['version'],
                ))
            elif dependency_uninstalled:
                # If a dependency of this one needs to be uninstalled, always uninstall the package
                self.uninstall_queue.append(dependency)
                self.logger.info('  {}: Uninstall and Reinstall to allow downgrade of dependency'.format(
                    dependency['namespace'],
                ))
            elif required_version < installed_version:
                # Uninstall to downgrade
                self.uninstall_queue.append(dependency)
                self.logger.info('  {}: Downgrade from {} to {} (requires uninstall/install)'.format(
                    dependency['namespace'],
                    installed_version,
                    dependency['version'],
                ))
            else:
                self.logger.info('  {}: Upgrade from {} to {}'.format(
                    dependency['namespace'],
                    installed_version,
                    dependency['version'],
                ))
            self.install_queue.append(dependency)
        else:
            # Just a regular install
            self.logger.info('  {}: Install version {}'.format(
                    dependency['namespace'],
                    dependency['version'],
            ))
            self.install_queue.append(dependency)

    def _get_installed(self):
        self.logger.info('Retrieving list of packages from target org')
        api = ApiRetrieveInstalledPackages(self)
        return api()

    def _uninstall_dependencies(self):
        for dependency in self.uninstall_queue:
            self._uninstall_dependency(dependency)

    def _install_dependencies(self):
        for dependency in self.install_queue:
            self._install_dependency(dependency)

    def _install_dependency(self, dependency):
        if 'zip_url' in dependency:
            self.logger.info('Deploying unmanaged metadata from /{} of {}'.format(
                dependency['subfolder'],
                dependency['zip_url'],
            ))
            package_zip = download_extract_zip(
                dependency['zip_url'],
                subfolder=dependency.get('subfolder')
            )
            if dependency.get('namespace_tokenize'):
                self.logger.info('Replacing namespace prefix {}__ in files and filenames with namespace token strings'.format(
                    '{}__'.format(dependency['namespace_tokenize']),
                ))
                package_zip = zip_tokenize_namespace(
                    package_zip,
                    namespace = dependency['namespace_tokenize'],
                )
                
            if dependency.get('namespace_inject'):
                self.logger.info('Replacing namespace tokens with {}'.format(
                    '{}__'.format(dependency['namespace_inject']),
                ))
                package_zip = zip_inject_namespace(
                    package_zip,
                    namespace = dependency['namespace_inject'],
                    managed = not dependency.get('unmanaged'),
                )
                
            if dependency.get('namespace_strip'):
                self.logger.info('Removing namespace prefix {}__ from all files and filenames'.format(
                    '{}__'.format(dependency['namespace_strip']),
                ))
                package_zip = zip_strip_namespace(
                    package_zip,
                    namespace = dependency['namespace_strip'],
                )
                
            package_zip = ZipfilePackageZipBuilder(package_zip)()

        elif 'namespace' in dependency:
            self.logger.info('Installing {} version {}'.format(
                dependency['namespace'],
                dependency['version'],
            ))
            package_zip = InstallPackageZipBuilder(dependency['namespace'], dependency['version'])()
            
        api = self.api_class(self, package_zip, purge_on_delete=self.options['purge_on_delete'])
        return api()

    def _uninstall_dependency(self, dependency):
        self.logger.info('Uninstalling {}'.format(dependency['namespace']))
        package_zip = UninstallPackageZipBuilder(
            dependency['namespace'],
            self.project_config.project__package__api_version,
        )
        api = self.api_class(self, package_zip(), purge_on_delete=self.options['purge_on_delete'])
        return api()

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

        self.logger.info(
            'Deploying all metadata bundles in path {}'.format(path))

        if not os.path.isdir(path):
            self.logger.warn('Path {} not found, skipping'.format(path))
            return

        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if not os.path.isdir(item_path):
                continue

            self.logger.info('Deploying bundle: {}/{}'.format(self.options['path'], item))

            self._deploy_bundle(item_path)

    def _deploy_bundle(self, path):
        api = self._get_api(path)
        return api()

deploy_namespaced_options = Deploy.task_options.copy()
deploy_namespaced_options.update({
    'managed': {
        'description': 'If True, will insert the actual namespace prefix.  Defaults to False or no namespace',
    },
    'namespace': {
        'description': 'The namespace to replace the token with if in managed mode. Defaults to project__package__namespace',
    },
    'namespace_token': {
        'description': 'The string token to replace with the namespace.  Defaults to %%%NAMESPACE%%%',
    },
    'filename_token': {
        'description': 'The path to the parent directory containing the metadata bundles directories. Defaults to ___NAMESPACE___',
    },
})

class DeployNamespaced(Deploy):
    task_options = deploy_namespaced_options

    def _init_options(self, kwargs):
        super(DeployNamespaced, self)._init_options(kwargs)

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

        zip_path = path.replace(self.options['filename_token'], namespace)
        with open(os.path.join(root, path), 'r') as f:
            content = f.read().replace(self.options['namespace_token'], namespace)
        if root == '.':
            zipf.writestr(zip_path, content)
        else:
            # strip ./ from the start of root
            root = root[2:]
            zipf.writestr(os.path.join(root, zip_path), content)


class DeployNamespacedBundles(DeployNamespaced, DeployBundles):
    name = 'DeployNamespacedBundles'


class BaseUninstallMetadata(Deploy):

    def _get_api(self, path=None):
        destructive_changes = self._get_destructive_changes(path=path)
        if not destructive_changes:
            return
        package_zip = DestructiveChangesZipBuilder(
            destructive_changes,
            self.project_config.project__package__api_version,
        )
        api = self.api_class(self, package_zip(), purge_on_delete=self.options['purge_on_delete'])
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
        'purge_on_delete': {
            'description': 'Sets the purgeOnDelete option for the deployment.  Defaults to True',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(UninstallPackaged, self)._init_options(kwargs)
        if 'package' not in self.options:
            self.options['package'] = self.project_config.project__package__name
        if 'purge_on_delete' not in self.options:
            self.options['purge_on_delete'] = True
        if self.options['purge_on_delete'] == 'False':
            self.options['purge_on_delete'] = False

    def _retrieve_packaged(self):
        retrieve_api = ApiRetrievePackaged(
            self,
            self.options['package'],
            self.project_config.project__package__api_version
        )
        packaged = retrieve_api()
        packaged = zip_subfolder(packaged, self.options['package'])
        return packaged

    def _get_destructive_changes(self, path=None):
        self.logger.info('Retrieving metadata in package {} from target org'.format(self.options['package']))
        packaged = self._retrieve_packaged()

        tempdir = tempfile.mkdtemp()
        packaged.extractall(tempdir)

        destructive_changes = super(UninstallPackaged, self)._get_destructive_changes(tempdir)

        shutil.rmtree(tempdir)

        self.logger.info('Deleting metadata in package {} from target org'.format(self.options['package']))
        return destructive_changes

class UninstallPackagedIncremental(UninstallPackaged):
    name = 'UninstallPackagedIncremental'
    skip_types = ['RecordType','Scontrol']
    task_options = {
        'path': {
            'description': 'The local path to compare to the retrieved packaged metadata from the org.  Defaults to src',
            'required': True,
        },
        'package': {
            'description': 'The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name',
            'required': True,
        },
        'purge_on_delete': {
            'description': 'Sets the purgeOnDelete option for the deployment.  Defaults to True',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(UninstallPackagedIncremental, self)._init_options(kwargs)
        if 'path' not in self.options:
            self.options['path'] = 'src'
        if 'purge_on_delete' not in self.options:
            self.options['purge_on_delete'] = True
        if self.options['purge_on_delete'] == 'False':
            self.options['purge_on_delete'] = False

    def _get_destructive_changes(self, path=None):
        self.logger.info('Retrieving metadata in package {} from target org'.format(self.options['package']))
        packaged = self._retrieve_packaged()

        tempdir = tempfile.mkdtemp()
        packaged.extractall(tempdir)

        destructive_changes = self._package_xml_diff(
            os.path.join(self.options['path'], 'package.xml'),
            os.path.join(tempdir, 'package.xml'),
        )

        shutil.rmtree(tempdir)
        if destructive_changes:
            self.logger.info('Deleting metadata in package {} from target org'.format(self.options['package']))
        else:
            self.logger.info('No metadata found to delete')
        return destructive_changes

    def _package_xml_diff(self, master, compare):
        master_xml = xmltodict.parse(open(master, 'r'))
        compare_xml = xmltodict.parse(open(compare, 'r'))

        delete = {}

        master_items = {}
        compare_items = {}
        md_types = master_xml['Package'].get('types', [])
        if not isinstance(md_types, list):
            # needed when only 1 metadata type is found
            md_types = [md_types]
        for md_type in md_types:
            master_items[md_type['name']] = []
            if 'members' not in md_type:
                continue
            if isinstance(md_type['members'], unicode):
                master_items[md_type['name']].append(md_type['members'])
            else:
                for item in md_type['members']:
                    master_items[md_type['name']].append(item)

        md_types = compare_xml['Package'].get('types', [])
        if not isinstance(md_types, list):
            # needed when only 1 metadata type is found
            md_types = [md_types]
        for md_type in md_types:
            compare_items[md_type['name']] = []
            if 'members' not in md_type:
                continue
            if isinstance(md_type['members'], unicode):
                compare_items[md_type['name']].append(md_type['members'])
            else:
                for item in md_type['members']:
                    compare_items[md_type['name']].append(item)

        for md_type, members in compare_items.items():
            if md_type not in master_items:
                delete[md_type] = members
                continue

            for member in members:
                if member not in master_items[md_type]:
                    if md_type not in delete:
                        delete[md_type] = []
                    delete[md_type].append(member)

        if delete:
            self.logger.info('Deleting metadata:')
            for skip_type in self.skip_types:
                delete.pop(skip_type, None)
            for md_type, members in delete.items():
                for member in members:
                    self.logger.info('    {}: {}'.format(md_type, member))
            destructive_changes = self._render_xml_from_items_dict(delete)
            return destructive_changes

    def _render_xml_from_items_dict(self, items):
        return package_xml_from_dict(
            items, 
            api_version = self.project_config.project__package__api_version,
        )

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
        'purge_on_delete': {
            'description': 'Sets the purgeOnDelete option for the deployment.  Defaults to True',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(UninstallLocalNamespacedBundles, self)._init_options(kwargs)

        if 'managed' not in self.options:
            self.options['managed'] = False

        if 'namespace' not in self.options:
            self.options['namespace'] = self.project_config.project__package__namespace
        if 'purge_on_delete' not in self.options:
            self.options['purge_on_delete'] = True
        if self.options['purge_on_delete'] == 'False':
            self.options['purge_on_delete'] = False

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
        destructive_changes = destructive_changes.replace(self.options['filename_token'], namespace)

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


class PackageUpload(BaseSalesforceApiTask):
    name = 'PackageUpload'
    api_version = '38.0'
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
        package_res = sf.query("select Id from MetadataPackage where NamespacePrefix='{}'".format(self.options['namespace']))

        if package_res['totalSize'] != 1:
            message = 'No package found with namespace {}'.format(self.options['namespace'])
            self.logger.error(message)
            raise SalesforceException(message)

        package_id = package_res['records'][0]['Id']

        production = self.options.get('production', False) in [True, 'True', 'true']
        package_info = {
            'VersionName': self.options['name'],
            'IsReleaseVersion': production,
            'MetadataPackageId': package_id,
        }

        if 'description' in self.options:
            package_info['Description'] = self.options['description']
        if 'password' in self.options:
            package_info['Password'] = self.options['password']
        if 'post_install_url' in self.options:
            package_info['PostInstallUrl'] = self.options['post_install_url']
        if 'release_notes_url' in self.options:
            package_info['ReleaseNotesUrl'] = self.options['release_notes_url']

        PackageUploadRequest = self._get_tooling_object('PackageUploadRequest')
        upload = PackageUploadRequest.create(package_info)
        upload_id = upload['id']

        soql_check_upload = "select Status, Errors, MetadataPackageVersionId from PackageUploadRequest where Id = '{}'".format(upload['id'])

        upload = self.tooling.query(soql_check_upload)
        if upload['totalSize'] != 1:
            message = 'Failed to get info for upload with id {}'.format(upload_id)
            self.logger.error(message)
            raise SalesforceException(message)
        upload = upload['records'][0]

        while upload['Status'] == 'IN_PROGRESS':
            time.sleep(3)
            upload = self.tooling.query(soql_check_upload)
            if upload['totalSize'] != 1:
                message = 'Failed to get info for upload with id {}'.format(upload_id)
                self.logger.error(message)
                raise SalesforceException(message)
            upload = upload['records'][0]

        if upload['Status'] == 'ERROR':
            self.logger.error('Package upload failed with the following errors')
            for error in upload['Errors']['errors']:
                self.logger.error('  {}'.format(error['message']))
            raise SalesforceException('Package upload failed')
        else:
            version_id = upload['MetadataPackageVersionId']
            version_res = self.tooling.query("select MajorVersion, MinorVersion, PatchVersion, BuildNumber, ReleaseState from MetadataPackageVersion where Id = '{}'".format(version_id))
            if version_res['totalSize'] != 1:
                message = 'Version {} not found'.format(version_id)
                self.logger.error(message)
                raise SalesforceException(message)

            version = version_res['records'][0]
            version_parts = [
                str(version['MajorVersion']),
                str(version['MinorVersion']),
            ]
            if version['PatchVersion']:
                version_parts.append(str(version['PatchVersion']))

            self.version_number = '.'.join(version_parts)

            if version['ReleaseState'] == 'Beta':
                self.version_number += ' (Beta {})'.format(version['BuildNumber'])

            self.return_values = {'version_number': self.version_number}

            self.logger.info('Uploaded package version {} with Id {}'.format(
                self.version_number,
                version_id
            ))



class RunApexTests(BaseSalesforceApiTask):
    task_options = {
        'test_name_match': {
            'description': ('Query to find Apex test classes to run ' +
                            '("%" is wildcard).  Defaults to ' +
                            'project__test__name_match'),
            'required': True,
        },
        'test_name_exclude': {
            'description': ('Query to find Apex test classes to exclude ' +
                            '("%" is wildcard).  Defaults to ' +
                            'project__test__name_exclude'),
        },
        'namespace': {
            'description': ('Salesforce project namespace.  Defaults to ' +
                            'project__package__namespace'),
        },
        'managed': {
            'description': ('If True, search for tests in the namespace ' +
                            'only.  Defaults to False'),
        },
        'poll_interval': {
            'description': ('Seconds to wait between polling for Apex test ' +
                            'results.  Defaults to 3'),
        },
        'retries': {
            'description': 'Number of retries (default=10)',
        },
        'retry_interval': {
            'description': 'Number of seconds to wait before the next retry (default=5),'
        },
        'retry_interval_add': {
            'description': 'Number of seconds to add before each retry (default=5),'
        },
        'junit_output': {
            'description': 'File name for JUnit output.  Defaults to test_results.xml',
        },
    }

    def _init_options(self, kwargs):
        super(RunApexTests, self)._init_options(kwargs)
        if 'test_name_match' not in self.options:
            self.options['test_name_match'] = self.project_config.project__test__name_match
        if 'test_name_exclude' not in self.options:
            self.options['test_name_exclude'] = self.project_config.project__test__name_exclude
        if self.options['test_name_exclude'] is None:
            self.options['test_name_exclude'] = ''
        if 'namespace' not in self.options:
            self.options['namespace'] = self.project_config.project__package__namespace
        if 'managed' not in self.options:
            self.options['managed'] = False
        else:
            if self.options['managed'] in [True, 'True', 'true']:
                self.options['managed'] = True
            else:
                self.options['managed'] = False
        if 'retries' not in self.options:
            self.options['retries'] = 10
        if 'retry_interval' not in self.options:
            self.options['retry_interval'] = 5
        if 'retry_interval_add' not in self.options:
            self.options['retry_interval_add'] = 5
        if 'junit_output' not in self.options:
            self.options['junit_output'] = 'test_results.xml'

        self.counts = {}

    def _init_class(self):
        self.classes_by_id = {}
        self.classes_by_name = {}
        self.job_id = None
        self.results_by_class_name = {}
        self._debug_init_class()
        self.result = None

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
        if self.options['managed']:
            namespace = self.options.get('namespace')
            if not namespace:
                raise TaskOptionsError(
                    'Running tests in managed mode but no namespace available.'
                )
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
        self.counts = {
            'Pass': 0,
            'Fail': 0,
            'CompileFail': 0,
            'Skip': 0,
        }
        for test_result in result['records']:
            class_name = self.classes_by_id[test_result['ApexClassId']]
            self.results_by_class_name[class_name][test_result[
                'MethodName']] = test_result
            self.counts[test_result['Outcome']] += 1
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
                             self.counts['Pass'],
                             self.counts['Fail'],
                             self.counts['CompileFail'],
                             self.counts['Skip'],
                         ))
        self.logger.info('-' * 80)
        if self.counts['Fail'] or self.counts['CompileFail']:
            self.logger.error('-' * 80)
            self.logger.error('Failing Tests')
            self.logger.error('-' * 80)
            counter = 0
            for result in test_results:
                if result['Outcome'] not in ['Fail', 'CompileFail']:
                    continue
                counter += 1
                self.logger.error('{}: {}.{} - {}'.format(counter,
                    result['ClassName'], result['Method'], result['Outcome']))
                self.logger.error('\tMessage: {}'.format(result['Message']))
                self.logger.error('\tStackTrace: {}'.format(
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
        result = self.tooling._call_salesforce(
            method='POST',
            url=self.tooling.base_url + 'runTestsAsynchronous',
            json={'classids': ','.join(str(id) for id in ids)},
        )
        if result.status_code != 200:
            raise SalesforceGeneralError(url,
                                         path,
                                         result.status_code,
                                         result.content)
        self.job_id = result.json()
        self._wait_for_tests()
        test_results = self._get_test_results()
        self._write_output(test_results)
        if self.counts.get('Fail') or self.counts.get('CompileFail'):
            total = self.counts.get('Fail') + self.counts.get('CompileFail')
            raise ApexTestException(
                '{} tests failed and {} tests failed compilation'.format(
                    self.counts.get('Fail'), self.counts.get('CompileFail')
                )
            )

    def _wait_for_tests(self):
        self._poll_interval_s = int(self.options.get('poll_interval', 1))
        self._poll()

    def _poll_action(self):
        self._retry()
        counts = {
            'Aborted': 0,
            'Completed': 0,
            'Failed': 0,
            'Holding': 0,
            'Preparing': 0,
            'Processing': 0,
            'Queued': 0,
        }
        for test_queue_item in self.result['records']:
            counts[test_queue_item['Status']] += 1
        self.logger.info('Completed: {}  Processing: {}  Queued: {}'.format(
            counts['Completed'],
            counts['Processing'],
            counts['Queued'],
        ))
        if counts['Queued'] == 0 and counts['Processing'] == 0:
            self.logger.info('Apex tests completed')
            self.poll_complete = True

    def _try(self):
        self.result = self.tooling.query_all(
            "SELECT Id, Status, ApexClassId FROM ApexTestQueueItem " +
            "WHERE ParentJobId = '{}'".format(self.job_id))

    def _write_output(self, test_results):
        junit_output = self.options['junit_output']
        with io.open(junit_output, mode='w', encoding='utf-8') as f:
            f.write(u'<testsuite tests="{}">\n'.format(len(test_results)))
            for result in test_results:
                s = '  <testcase classname="{}" name="{}"'.format(
                    result['ClassName'], result['Method'])
                if ('Stats' in result and result['Stats']
                        and 'duration' in result['Stats']):
                    s += ' time="{}"'.format(result['Stats']['duration'])
                if result['Outcome'] in ['Fail', 'CompileFail']:
                    s += '>\n'
                    s += ('    <failure type="failed" ' +
                        'message="{}"><![CDATA[{}]]></failure>\n'.format(
                            cgi.escape(result['Message']),
                            cgi.escape(result['StackTrace']),
                        )
                    )
                    s += '  </testcase>\n'
                else:
                    s += ' />\n'
                f.write(unicode(s))
            f.write(u'</testsuite>')

run_apex_tests_debug_options = RunApexTests.task_options.copy()
run_apex_tests_debug_options.update({
    'debug_log_dir': {
        'description': 'Directory to store debug logs. Defaults to temp dir.',
    },
    'json_output': {
        'description': ('The path to the json output file.  Defaults to ' +
                       'test_results.json'),
    }
})

class RunApexTestsDebug(RunApexTests):
    """Run Apex tests and collect debug info"""
    api_version = '38.0'
    task_options = run_apex_tests_debug_options

    def _init_options(self, kwargs):
        super(RunApexTestsDebug, self)._init_options(kwargs)
        if 'json_output' not in self.options:
            self.options['json_output'] = 'test_results.json'

    def _debug_init_class(self):
        self.classes_by_log_id = {}
        self.logs_by_class_id = {}
        self.trace_id = None

    def _debug_create_trace_flag(self):
        """Create a TraceFlag for a given user."""
        self._delete_debug_levels()
        self._delete_trace_flags()
        self.logger.info('Creating DebugLevel object')
        DebugLevel = self._get_tooling_object('DebugLevel')
        result = DebugLevel.create({
            'ApexCode': 'Info',
            'ApexProfiling': 'Debug',
            'Callout': 'Info',
            'Database': 'Info',
            'DeveloperName': 'CumulusCI',
            'MasterLabel': 'CumulusCI',
            'System': 'Info',
            'Validation': 'Info',
            'Visualforce': 'Info',
            'Workflow': 'Info',
        })
        self.debug_level_id = result['id']
        self.logger.info('Setting up trace flag to capture debug logs')
        # New TraceFlag expires 12 hours from now
        expiration_date = (datetime.datetime.utcnow() +
            datetime.timedelta(seconds=60*60*12))
        TraceFlag = self._get_tooling_object('TraceFlag')
        result = TraceFlag.create({
            'DebugLevelId': result['id'],
            'ExpirationDate': expiration_date.isoformat(),
            'LogType': 'USER_DEBUG',
            'TracedEntityId': self.org_config.user_id,
        })
        self.trace_id = result['id']
        self.logger.info('Created TraceFlag for user')

    def _delete_trace_flags(self):
        """
        Delete existing DebugLevel objects.
        This will automatically delete associated TraceFlags as well.
        """
        self.logger.info('Deleting existing TraceFlag objects')
        result = self.tooling.query(
            "Select Id from TraceFlag Where TracedEntityId = '{}'".format(
                self.org_config.user_id
            )
        )
        if result['totalSize']:
            TraceFlag = self._get_tooling_object('TraceFlag')
            for record in result['records']:
                TraceFlag.delete(str(record['Id']))

    def _delete_debug_levels(self):
        """
        Delete existing DebugLevel objects.
        This will automatically delete associated TraceFlags as well.
        """
        self.logger.info('Deleting existing DebugLevel objects')
        result = self.tooling.query('Select Id from DebugLevel')
        if result['totalSize']:
            DebugLevel = self._get_tooling_object('DebugLevel')
            for record in result['records']:
                DebugLevel.delete(str(record['Id']))

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
        debug_log_dir = self.options.get('debug_log_dir')
        if debug_log_dir:
            tempdir = None
            try:
                os.makedirs(debug_log_dir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
        else:
            tempdir = tempfile.mkdtemp()
        for log in result['records']:
            class_id = self.classes_by_log_id[log['Id']]
            class_name = self.classes_by_id[class_id]
            self.logs_by_class_id[class_id] = log
            body_url = '{}sobjects/ApexLog/{}/Body'.format(
                self.tooling.base_url, log['Id'])
            response = self.tooling.request.get(body_url,
                headers=self.tooling.headers)
            log_file = class_name + '.log'
            if debug_log_dir:
                log_file = os.path.join(debug_log_dir, log_file)
            else:
                log_file = os.path.join(tempdir, log_file)
            with io.open(log_file, mode='w', encoding='utf-8') as f:
                f.write(self._decode_to_unicode(response.content))
            with io.open(log_file, mode='r', encoding='utf-8') as f:
                method_stats = self._parse_log(class_name, f)
            # Add method stats to results_by_class_name
            for method, info in method_stats.items():
                if method not in self.results_by_class_name[class_name]:
                    # Ignore lines that aren't from a test method such as the @testSetup decorated method
                    continue
                self.results_by_class_name[class_name][method].update(info)
        # Delete the DebugLevel
        DebugLevel = self._get_tooling_object('DebugLevel')
        DebugLevel.delete(str(self.debug_level_id))
        # Clean up tempdir logs
        if tempdir:
            shutil.rmtree(tempdir)

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
        # Write the JUnit test report
        super(RunApexTestsDebug, self)._write_output(test_results)

        # Write the json file
        json_output = self.options['json_output']
        with io.open(json_output, mode='w', encoding='utf-8') as f:
            f.write(unicode(json.dumps(test_results)))

class SOQLQuery(BaseSalesforceApiTask):
    name = 'SOQLQuery'

    task_options = {
        'object' : {'required':True, 'description':'The object to query'},
        'query' : {'required':True, 'description':'A valid bulk SOQL query for the object'},
        'result_file' : {'required':True,'description':'The name of the csv file to write the results to'}
    }

    def _run_task(self):
        self.logger.info('Creating bulk job for: {object}'.format(**self.options))
        job = self.bulk.create_query_job(self.options['object'], contentType='CSV')
        self.logger.info('Job id: {0}'.format(job))
        self.logger.info('Submitting query: {query}'.format(**self.options))
        batch = self.bulk.query(job,self.options['query'])
        self.logger.info('Batch id: {0}'.format(batch))
        self.bulk.wait_for_batch(job,batch)
        self.logger.info('Batch {0} finished'.format(batch))
        self.bulk.close_job(job)
        self.logger.info('Job {0} closed'.format(job))
        with open(self.options['result_file'],"w") as result_file:
            for row in self.bulk.get_batch_result_iter(job,batch):
                result_file.write(row+'\n')
        self.logger.info('Wrote results to: {result_file}'.format(**self.options))
