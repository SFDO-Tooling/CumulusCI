import os
import shutil
import time
import glob
from xml.dom.minidom import parse

from cumulusci.core.tasks import BaseTask
from cumulusci.utils import download_extract_zip


class DownloadZip(BaseTask):
    name = 'Download'
    task_options = {
        'url': {
            'description': 'The url of the zip file to download',
            'required': True,
        },
        'dir': {
            'description': 'The directory where the zip should be extracted',
            'required': True,
        },
        'subfolder': {
            'description': (
                'The subfolder of the target zip to extract. Defaults to' +
                ' extracting the root of the zip file to the destination.'
            ),
        },
    }

    def _run_task(self):
        if not self.options['dir']:
            self.options['dir'] = '.'
        elif not os.path.exists(self.options['dir']):
            os.makedirs(self.options['dir'])

        download_extract_zip(
            self.options['url'],
            self.options['dir'],
            self.options.get('subfolder'),
        )


class ListMetadataTypes(BaseTask):
    name = 'ListMetadataTypes'
    task_options = {
        'package_xml': {'description': (
            'The project package.xml file.' +
            ' Defaults to <project_root>/src/package.xml'
        )}
    }

    def _init_options(self, kwargs):
        super(ListMetadataTypes, self)._init_options(kwargs)
        if 'package_xml' not in self.options:
            self.options['package_xml'] = os.path.join(
                self.project_config.repo_root,
                'src',
                'package.xml',
            )

    def _run_task(self):
        dom = parse(self.options['package_xml'])
        package = dom.getElementsByTagName('Package')[0]
        types = package.getElementsByTagName('types')
        type_list = []
        for t in types:
            name = t.getElementsByTagName('name')[0]
            metadata_type = name.firstChild.nodeValue
            type_list.append(metadata_type)
        self.logger.info(
            'Metadata types found in %s:\r\n%s',
            self.options['package_xml'],
            '\r\n'.join(type_list),
        )


class Sleep(BaseTask):
    name = 'Sleep'
    task_options = {
        'seconds': {
            'description': 'The number of seconds to sleep',
            'required': True,
        },
    }

    def _run_task(self):
        self.logger.info(
            'Sleeping for {} seconds'.format(self.options['seconds'])
        )
        time.sleep(float(self.options['seconds']))
        self.logger.info('Done')

class Delete(BaseTask):
    name = 'Delete'
    task_options = {
        'path': {
            'description': 'The path to delete.  If path is a directory, recursively deletes the directory: BE CAREFUL!!!  If path is a list, all paths will be deleted',
            'required': True,
        },
        'chdir': {
            'description': 'Change directories before deleting path(s).  This is useful if you have a common list of relative paths to delete that you want to call against different directories.',
        }
    }

    def _run_task(self):
        chdir = self.options.get('chdir')
        cwd = os.getcwd()
        if chdir:
            self.logger.info(
                'Changing directory to {}'.format(chdir)
            )
            os.chdir(chdir)

        path = self.options['path']
        if isinstance(path, list):
            for path_item in path:
                for match in glob.glob(path_item):
                    self._delete(match)
   
        if chdir: 
            os.chdir(cwd)

    def _delete(self, path):
        if not os.path.exists(path):
            self.logger.info(
                '{} does not exist, skipping delete'.format(path)
            )
        if os.path.isdir(path):
            self.logger.info(
                'Recursively deleting directory {}'.format(path)
            )
            shutil.rmtree(path)
        else:
            self.logger.info(
                'Deleting file {}'.format(path)
            )
            os.remove(path)
