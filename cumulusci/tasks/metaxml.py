import os
import re
from lxml import etree as ET

from cumulusci.core.tasks import BaseTask


class UpdateDependencies(BaseTask):
    task_options = {
        'dir': {
            'description': 'Base directory to search for *-meta.xml files',
        },
        'namespace': {
            'description': 'Package namespace e.g. npe01',
            'required': True,
        },
        'version': {
            'description': 'Package version number e.g. 1.2',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(UpdateDependencies, self)._init_options(kwargs)
        if 'dir' not in self.options or not self.options['dir']:
            self.options['dir'] = os.path.join(
                self.project_config.repo_root,
                'src',
            )
        self.v_major, self.v_minor = self.options['version'].split('.')

    def _run_task(self):
        for root, dirs, files in os.walk(self.options['dir']):
            for filename in files:
                if filename.endswith('-meta.xml'):
                    self._process_file(os.path.join(root, filename))

    def _process_file(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        xmlns = re.search('({.+}).+', root.tag).group(1)
        changed = False
        for package_version in root.findall('{}packageVersions'.format(xmlns)):
            namespace = package_version.find('{}namespace'.format(xmlns)).text
            if namespace != self.options['namespace']:
                continue
            changed = True
            major = package_version.find('{}majorNumber'.format(xmlns))
            major.text = self.v_major
            minor = package_version.find('{}minorNumber'.format(xmlns))
            minor.text = self.v_minor
        if changed:
            tree.write(
                filename,
                xml_declaration=True,
                encoding='UTF-8',
                pretty_print=True,
            )
            self.logger.info('Processed file %s', filename)
        else:
            self.logger.info('No changes for file %s', filename)
