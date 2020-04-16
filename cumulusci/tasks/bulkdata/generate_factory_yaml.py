from pathlib import Path

from cumulusci.tasks.github.base import BaseGithubTask


class GenerateFactoryYaml(BaseGithubTask):
    task_docs = """
    Generate factory YAML for the project by walking all GitHub releases.
    Both MDAPI and SFDX format releases are supported. However, only force-app/main/default
    is processed for SFDX projects.
    """

    task_options = {
        "yaml_output": {"description": "Path to a YAML file to generate."},
        "objects": {
            "description": "Comma-separated list of objects to output or '*' to output all"
        },
        "release_prefix": {
            "description": "The tag prefix used for releases.",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        yaml_output = self.options.get("yaml_output")
        if yaml_output:
            self.yaml_output = Path(yaml_output)
        else:
            self.yaml_output = Path("factory_yaml.yml")

        with open(self.yaml_output, "w"):
            pass  # check it is writable
