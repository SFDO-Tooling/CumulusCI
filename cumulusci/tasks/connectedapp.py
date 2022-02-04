import json
import os
import re

from cumulusci.core.config import ServiceConfig
from cumulusci.core.exceptions import ServiceNotConfigured, TaskOptionsError
from cumulusci.core.keychain import DEFAULT_CONNECTED_APP
from cumulusci.core.utils import process_bool_arg
from cumulusci.oauth.client import PROD_LOGIN_URL
from cumulusci.tasks.sfdx import SFDX_CLI, SFDXBaseTask
from cumulusci.utils import random_alphanumeric_underscore, temporary_dir

CONNECTED_APP = """<?xml version="1.0" encoding="UTF-8"?>
<ConnectedApp xmlns="http://soap.sforce.com/2006/04/metadata">
    <contactEmail>{email}</contactEmail>
    <label>{label}</label>
    <oauthConfig>
        <callbackUrl>http://localhost:8080/callback</callbackUrl>
        <consumerKey>{client_id}</consumerKey>
        <consumerSecret>{client_secret}</consumerSecret>
        <scopes>Web</scopes>
        <scopes>Full</scopes>
        <scopes>RefreshToken</scopes>
    </oauthConfig>
</ConnectedApp>"""

PACKAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>*</members>
        <name>ConnectedApp</name>
    </types>
    <version>44.0</version>
</Package>"""


class CreateConnectedApp(SFDXBaseTask):
    client_id_length = 85
    client_secret_length = 32
    deploy_wait = 5
    task_options = {
        "label": {
            "description": "The label for the connected app.  Must contain only alphanumeric and underscores",
            "required": True,
        },
        "email": {
            "description": "The email address to associate with the connected app.  Defaults to email address from the github service if configured."
        },
        "username": {
            "description": "Create the connected app in a different org.  Defaults to the defaultdevhubusername configured in sfdx.",
            "required": False,
        },
        "connect": {
            "description": "If True, the created connected app will be stored as the CumulusCI connected_app service in the keychain.",
            "required": False,
        },
        "overwrite": {
            "description": "If True, any existing connected_app service in the CumulusCI keychain will be overwritten.  Has no effect if the connect option is False.",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        self.client_id = None
        self.client_secret = None
        kwargs["command"] = "force:mdapi:deploy --wait {}".format(self.deploy_wait)
        super(CreateConnectedApp, self)._init_options(kwargs)

        # Validate label
        if not re.match(r"^\w+$", self.options["label"]):
            raise TaskOptionsError(
                "label value must contain only alphanumeric or underscore characters"
            )

        # Default email to the github service's email if configured
        if "email" not in self.options:
            try:
                github = self.project_config.keychain.get_service("github")
            except ServiceNotConfigured:
                raise TaskOptionsError(
                    "Could not determine a default for option 'email'.  Either configure the github service using 'cci service connect github' or provide a value for the 'email' option"
                )
            self.options["email"] = github.email

        self.options["connect"] = process_bool_arg(self.options.get("connect") or False)
        self.options["overwrite"] = process_bool_arg(
            self.options.get("overwrite") or False
        )

    def _set_default_username(self):
        self.logger.info("Getting username for the default devhub from sfdx")
        output = []
        self._run_command(
            command="{} force:config:get defaultdevhubusername --json".format(SFDX_CLI),
            env=self._get_env(),
            output_handler=output.append,
        )
        self._process_devhub_output(b"\n".join(output))

    def _process_json_output(self, output):
        try:
            data = json.loads(output)
            return data
        except Exception:
            self.logger.error("Failed to parse json from output: {}".format(output))
            raise

    def _process_devhub_output(self, output):
        data = self._process_json_output(output)
        if "value" not in data["result"][0]:
            raise TaskOptionsError(
                "No sfdx config found for defaultdevhubusername.  Please use the sfdx force:config:set to set the defaultdevhubusername and run again"
            )
        self.options["username"] = data["result"][0]["value"]

    def _generate_id_and_secret(self):
        self.client_id = random_alphanumeric_underscore(self.client_id_length)
        self.client_secret = random_alphanumeric_underscore(self.client_secret_length)

    def _build_package(self):
        connected_app_path = "connectedApps"
        os.mkdir(connected_app_path)
        self._generate_id_and_secret()
        with open(
            os.path.join(connected_app_path, self.options["label"] + ".connectedApp"),
            "w",
        ) as f:
            f.write(
                CONNECTED_APP.format(
                    label=self.options["label"],
                    email=self.options["email"],
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                )
            )
        with open("package.xml", "w") as f:
            f.write(PACKAGE_XML)

    def _validate_connect_service(self):
        if not self.options["overwrite"]:
            try:
                connected_app = self.project_config.keychain.get_service(
                    "connected_app", self.options["label"]
                )
            except ServiceNotConfigured:  # pragma: no cover
                pass
            else:
                if connected_app is not DEFAULT_CONNECTED_APP:
                    raise TaskOptionsError(
                        "The CumulusCI keychain already contains a connected_app service.  Set the 'overwrite' option to True to overwrite the existing service"
                    )

    def _connect_service(self):
        self.project_config.keychain.set_service(
            "connected_app",
            self.options["label"],
            ServiceConfig(
                {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "login_url": PROD_LOGIN_URL,
                    "callback_url": "http://localhost:8080/callback",
                }
            ),
        )

    def _get_command(self):
        command = super()._get_command()
        # Default to sfdx defaultdevhubusername
        if "username" not in self.options:
            self._set_default_username()
        command += " -u {}".format(self.options.get("username"))
        command += " -d {}".format(self.tempdir)
        return command

    def _run_task(self):
        if self.options["connect"]:
            self._validate_connect_service()

        with temporary_dir() as tempdir:
            self.tempdir = tempdir
            self._build_package()
            super()._run_task()

        if self.options["connect"]:
            self._connect_service()
