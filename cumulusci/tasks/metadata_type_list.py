import sarge
import json
from cumulusci.core.tasks import BaseTask
from cumulusci.core.sfdx import sfdx

class MetadataTypeList(BaseTask):

    task_options = {       
        "org_username": {
            "description": "Username for the org",
            "required":True,
        },
    }

    def _run_task(self): 

        p: sarge.Command = sfdx(
            f"force mdapi describemetadata --json ",
           
            username=self.options["org_username"],
        )
        stdout = p.stdout_text.read()

        self.metadata_list=[]

        if  p.returncode:
            self.logger.error( f"Couldn't load list of Metadata types: \n{stdout}")

        else:
            data=json.loads(stdout)
            self.logger.info("List of Metadata types enabled for the org : ")

            for x in data['result']['metadataObjects']:
                self.metadata_list.append(x['xmlName'])
                self.metadata_list+=x['childXmlNames']

            self.logger.info(self.metadata_list)
       

       