import os
import shutil
import tempfile

import xmltodict

from cumulusci.tasks.salesforce import UninstallPackaged
from cumulusci.utils import package_xml_from_dict


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
