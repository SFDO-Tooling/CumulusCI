import glob
import os
import lxml.etree as ET
from xml.sax.saxutils import escape
from cumulusci.core.tasks import BaseTask

class RemoveElementsXPath(BaseTask):
    task_options = {
        'elements': {
            'description': 'A list of dictionaries containing path and xpath keys. The path key is a file path that supports wildcards and xpath is the xpath for the elements to remove.  Multiple dictionaries can be passed in the list to run multiple removal queries in the same task.  Metadata elements in the xpath need to be prefixed with ns:, for example: ./ns:Layout/ns:relatedLists',
            'required': True,
        },
        'chdir': {
            'description': 'Change the current directory before running the replace',
        }
    }

    def _run_task(self):
        cwd = os.getcwd()
        chdir = self.options.get('chdir')
        if chdir:
            self.logger.info('Changing directory to {}'.format(chdir))
            os.chdir(chdir)
        for element in self.options['elements']:
            self._process_element(element)
        if chdir:
            os.chdir(cwd)
   
    def _process_element(self, element):
        self.logger.info(
            'Removing elements matching {xpath} from {path}'.format(
                **element
            )
        )
        for f in glob.glob(element['path']):
            with open(f, 'rw') as fp:
                orig = fp.read()
                fp.seek(0)
                root = ET.parse(open(f))
                res = root.findall(element['xpath'].replace('ns:','{http://soap.sforce.com/2006/04/metadata}'))
                for element in res:
                    element.getparent().remove(element)
                processed = '{}\n{}\n'.format(
                    '<?xml version="1.0" encoding="UTF-8"?>',
                    ET.tostring(root),
                )
                if orig != processed:
                    self.logger.info('Modified {}'.format(f))
                    fp = open(f, 'w')
                    fp.write(processed)
