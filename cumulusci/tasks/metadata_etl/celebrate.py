import pathlib

from cumulusci.core.config import TaskConfig
from cumulusci.tasks.metadata_etl.base import BaseMetadataSynthesisTask
from cumulusci.tasks.robotframework.robotframework import Robot

PATH = """<?xml version="1.0" encoding="UTF-8"?>
<PathAssistant xmlns="http://soap.sforce.com/2006/04/metadata">
    <active>true</active>
    <entityName>Opportunity</entityName>
    <fieldName>StageName</fieldName>
    <masterLabel>Celebrate</masterLabel>
    <pathAssistantSteps>
        <info>{message}</info>
        <picklistValueName>Closed Won</picklistValueName>
    </pathAssistantSteps>
    <recordTypeName>__MASTER__</recordTypeName>
</PathAssistant>
"""

ANIMATION = """<?xml version="1.0" encoding="UTF-8"?>
<AnimationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <animationFrequency>always</animationFrequency>
    <developerName>Celebrate</developerName>
    <isActive>true</isActive>
    <masterLabel>Celebrate</masterLabel>
    <recordTypeContext>Master</recordTypeContext>
    <recordTypeName>__MASTER__</recordTypeName>
    <sobjectType>Opportunity</sobjectType>
    <targetField>StageName</targetField>
    <targetFieldChangeToValues>Closed Won</targetFieldChangeToValues>
</AnimationRule>
"""


class Celebrate(BaseMetadataSynthesisTask):

    task_options = {
        "message": {},
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

    def _synthesize(self):
        (self.deploy_dir / "pathAssistants").mkdir()
        (self.deploy_dir / "pathAssistants" / "Celebrate.path").write_text(
            PATH.format(message=self.options.get("message") or "")
        )
        (self.deploy_dir / "animationRules").mkdir()
        (self.deploy_dir / "animationRules" / "Celebrate.animationRule").write_text(
            ANIMATION
        )

    def _run_task(self):
        # deploy
        super()._run_task()

        # robot
        suite = pathlib.Path(__file__).parent / "celebrate.robot"
        task_config = TaskConfig({"options": {"suites": str(suite)}})
        task = Robot(self.project_config, task_config, self.org_config)
        task()
