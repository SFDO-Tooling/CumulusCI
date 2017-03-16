import os
import time

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
            'description': 'The subfolder of the target zip to extract.  Defaults to extracting the root of the zip file to the destination.',
        },
    }
   
    def _run_task(self):
        if not self.options['dir']:
            self.options['dir'] = '.'
        elif not os.path.exists(self.options['dir']):
            os.makedirs(self.options['dir'])
            
        download_extract_zip(self.options['url'], self.options['dir'], self.options.get('subfolder'))
         
    

class Sleep(BaseTask):
    name = 'Sleep'
    task_options = {
        'seconds': {
            'description': 'The number of seconds to sleep',
            'required': True,
        },
    } 
    
    def _run_task(self):
        self.logger.info("Sleeping for {} seconds".format(self.options['seconds']))
        time.sleep(float(self.options['seconds']))
        self.logger.info("Done")

