import json
import os
import sys
from pathlib import Path
from cumulusci.tasks.bulkdata import LoadData
from cumulusci.utils import cd
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
class LoadFromDatapy(BaseSalesforceApiTask):
    username = ""
    password = ""
    url = "https://login.salesforce.com/"
    api_version = "63.0"
    service_context_file_path = "service_context.json"
    task_docs = """
    Use the `config` option to specify the Config File Path which contains the script.
    Use the `api` option to specify the api version.
    Use 'service_context' option to specify the Service Context File Path which contains Org details.
    Use 'mode' to specify the mode of execution.
    User 'datapy_env' to specify the DataPy environment path where scripts with run (optional)
    """
    task_options = {
        "config": {
            "description": "Config file path for executing DataPy tests.",
            "required": True,
        },
        "api": {
            "description": "API version.",
            "required": True,
        },
        "namespace": {
            "description": "Service context file for the execution properties.",
            "required": True,
        },
        "client_secret": {
            "description": "Client secret of the connected app.",
            "required": True,
        },
        "client_id": {
            "description": "Client Id of the connected app.",
            "required": True,
        },
        "mode": {
            "description": "Execution mode.",
            "required": True,
        },
        "datapy_env": {
            "description": "DataPy environment Path checkout fork repository path",
            "required": False,
        },
        "username": {
            "description": "Username for the Org where script need to be triggered",
            "required": False,
        },
        "password": {
            "description": "Password for the Org where script need to be triggered",
            "required": False,
        },
        "instance_url": {
            "description": "Login url for the Org where script need to be triggered",
            "required": False,
        },
        **LoadData.task_options,
    }
    datapy_env_path = os.environ.get("DATAPY_FORKED_PATH")
    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        if self.options.get("datapy_env") is not None:
            self.datapy_env_path = self.options.get("datapy_env")
        print(self.datapy_env_path)
        if self.options.get("username") is not None:
            self.username = self.options.get("username")

        if self.options.get("password") is not None:
            self.password = self.options.get("password")
        
        if self.options.get("instance_url") is not None:
            self.url = self.options.get("instance_url")
        if self.options.get("api") is not None:
            self.api_version = self.options.get("api")
        data = {}
        # modify username and password in buffered content
        data["username"] = self.username
        data["password"] = self.password
        data["url"] = self.url
        connected_app = {}
        connected_app["client_id"] = self.options.get("client_id")
        connected_app["client_secret"] = self.options.get("client_secret")
        connected_app["grant_type"] = "password"
        data["connected_app"] = connected_app
        print("SERVICE CONTEXT:")
        print(data)
        # save changes to service context json file
        service_context_json_file = open(self.service_context_file_path, "w+")
        service_context_json_file.write(json.dumps(data))
        service_context_json_file.close()
    def _run_task(self):
        datapy_config = self.options.get("config")
        api_version = self.options.get("api")
        service_context = self.options.get("service_context")
        mode = self.options.get("mode")
        print("INPUT:")
        print(
            "Config File - " + str(datapy_config),
            "\nApi version - " + str(self.api_version),
            "\nService Context File - " + str(service_context),
            "\nMode of Execution - " + str(mode),
            )
        execution_command = (
                "./runner.sh --config "
                + str(datapy_config)
                + " --api "
                + str(api_version)
                + " --serviceContext "
                + str(service_context)
                + " --mode "
                + str(mode)
        )
        with cd(self.datapy_env_path):
            os.system("echo 'Running DataPy'")
            os.system(execution_command)
        return "DataPy Execution Completed Successfully"