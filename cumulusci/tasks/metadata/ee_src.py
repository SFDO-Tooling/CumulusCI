import os
from distutils.dir_util import copy_tree
from distutils.dir_util import remove_tree
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseTask
from cumulusci.utils import removeXmlElement

class CreateUnmanagedEESrc(BaseTask):
    task_options = {
        'path': {
            'description': 'The path containing metadata to process for managed deployment',
            'required': True,
        },
        'revert_path': {
            'description': 'The path to copy the original metadata to for the revert call',
            'required': True,
        },
    }

    elements = ['*.object:availableFields']

    def _run_task(self):
        # Check that path exists
        if not os.path.isdir(self.options['path']):
            raise TaskOptionsError(
                'The path {} does not exist or is not a directory'.format(
                    self.options['path'],
                )
            )

        # Check that revert_path does not exist
        if os.path.exists(self.options['revert_path']):
            raise TaskOptionsError(
                'The revert_path {} already exists.  Delete it and try again'.format(
                    self.options['revert_path'],
                )
            )

        # Copy path to revert_path
        copy_tree(self.options['path'], self.options['revert_path'])

        # Edit metadata in path
        self.logger.info('Preparing metadata in {0} for unmanaged EE deployment'.format(
            self.options['path'],
        )) 
        
        for element in self.elements:
            fname_match, element_name = element.split(':')
            removeXmlElement(
                element_name,
                os.path.join(self.options['path']),
                fname_match,
            )
    
        self.logger.info('Metadata in {} is now prepared for unmanaged EE deployment'.format(
            self.options['path'],
        ))

class RevertUnmanagedEESrc(BaseTask):
    task_options = {
        'path': {
            'description': 'The path containing metadata to process for managed deployment',
            'required': True,
        },
        'revert_path': {
            'description': 'The path to copy the original metadata to for the revert call',
            'required': True,
        },
    }

    def _run_task(self):
        # Check that revert_path does exists
        if not os.path.isdir(self.options['revert_path']):
            raise TaskOptionsError(
                'The revert_path {} does not exist or is not a directory'.format(
                    self.options['revert_path'],
                )
            )

        self.logger.info('Reverting {} from {}'.format(
            self.options['path'],
            self.options['revert_path'],
        ))
        copy_tree(self.options['revert_path'], self.options['path'], update=1)
        self.logger.info('{} is now reverted'.format(
            self.options['path'],
        ))

        # Delete the revert_path
        self.logger.info('Deleting {}'.format(
            self.options['revert_path'],
        ))
        remove_tree(self.options['revert_path'])
