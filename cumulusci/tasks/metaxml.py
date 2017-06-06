import os
import re
from lxml import etree as ET

from cumulusci.core.tasks import BaseTask


class MetaXmlBaseTask(BaseTask):

    def _init_options(self, kwargs):
        super(MetaXmlBaseTask, self)._init_options(kwargs)
        if 'dir' not in self.options or not self.options['dir']:
            self.options['dir'] = os.path.join(
                self.project_config.repo_root,
                'src',
            )

    def _run_task(self):
        for root, dirs, files in os.walk(self.options['dir']):
            for filename in files:
                if filename.endswith('-meta.xml'):
                    self._process_file(os.path.join(root, filename))


class UpdateApi(MetaXmlBaseTask):
    task_options = {
        'dir': {
            'description': 'Base directory to search for *-meta.xml files',
        },
        'version': {
            'description': 'API version number e.g. 37.0',
            'required': True,
        },
    }

    def _process_file(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        xmlns = re.search('({.+}).+', root.tag).group(1)
        changed = False
        api_version = root.find('{}apiVersion'.format(xmlns))
        if (api_version is not None and
                api_version.text != self.options['version']):
            api_version.text = self.options['version']
            changed = True
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


class UpdateDependencies(MetaXmlBaseTask):
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

    def _process_file(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        xmlns = re.search('({.+}).+', root.tag).group(1)
        changed = False
        v_major, v_minor = self.options['version'].split('.')
        for package_version in root.findall('{}packageVersions'.format(xmlns)):
            namespace = package_version.find('{}namespace'.format(xmlns)).text
            if namespace != self.options['namespace']:
                continue
            major = package_version.find('{}majorNumber'.format(xmlns))
            if major.text != v_major:
                major.text = v_major
                changed = True
            minor = package_version.find('{}minorNumber'.format(xmlns))
            if minor.text != v_minor:
                minor.text = v_minor
                changed = True
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
