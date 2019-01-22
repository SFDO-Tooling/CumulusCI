import json
import requests

from cumulusci.core.config import BaseConfig
from cumulusci.core.exceptions import PlanNotFound
from cumulusci.core.tasks import BaseTask
from cumulusci.core.flowrunner import FlowCoordinator


class Publish(BaseTask):
    """Publishes an installation plan to MetaDeploy.
    """

    task_options = {
        "plan": {
            "description": "Name of the installation plan to publish",
            "required": True,
        },
        "tag": {"description": "Name of git tag to publish"},
    }

    def _init_task(self):
        metadeploy_service = self.project_config.keychain.get_service("metadeploy")
        self.base_url = metadeploy_service.url
        self.api = requests.Session()
        self.api.headers["Authorization"] = "token {}".format(metadeploy_service.token)
        self.metadeploy_config = self.project_config.metadeploy
        if self.metadeploy_config is None:
            raise PlanNotFound(
                "No metadeploy configuration found. "
                "Did you forget to configure it in cumulusci.yml?"
            )
        plan_config = getattr(
            self.project_config, "metadeploy__plans__{}".format(self.options["plan"])
        )
        if plan_config is None:
            raise PlanNotFound("{} plan not found.".format(self.options["plan"]))
        self.plan_config = BaseConfig(plan_config)

    def _call_api(self, method, url, **kwargs):
        next_url = url
        results = []
        while next_url is not None:
            response = self.api.request(method, url, **kwargs)
            response.raise_for_status()
            response = response.json()
            if "links" in response:
                results.extend(response["data"])
                next_url = response["links"]["next"]
            else:
                return response
        return results

    def _run_task(self):
        tag = self.options["tag"]
        label = self.project_config.get_version_for_tag(tag)
        # @@@ handle checkout/publish from a release tag instead of current commit
        steps = self._freeze_steps()

        # create version (not listed yet)
        # @@@ only if doesn't already exist
        product_url = self.metadeploy_config["product_url"]
        version = self._call_api(
            "POST",
            self.base_url + "/versions",
            json={
                "product": product_url,
                "label": label,
                "description": tag,  # @@@ make it not required
                "is_production": True,
                "commit_ish": self.project_config.repo_commit,
                "is_listed": False,
            },
        )
        self.logger.info("Created {}".format(version["url"]))

        # create plan
        plan = self._call_api(
            "POST",
            self.base_url + "/plans",
            json={
                "title": self.plan_config.title,
                "version": version["url"],
                "preflight_message": self.plan_config.preflight_message,
                "tier": self.plan_config.tier or "primary",
                "post_install_message": self.plan_config.post_install_message,
                "steps": steps,
            },
        )
        self.logger.info("Created Plan {}".format(plan["url"]))

        # create plan slug
        planslug = self._call_api(
            "POST",
            self.base_url + "/planslugs",
            json={"parent": plan["url"], "slug": self.options["plan"]},
        )
        self.logger.info("Created PlanSlug {}".format(planslug["url"]))

        # update version to set is_listed=True
        self._call_api("PATCH", version["url"], json={"is_listed": True})
        self.logger.info("Published Version {}".format(version["url"]))
        # @@@ link to metadeploy frontend

    def _freeze_steps(self):
        flow_name = self.plan_config.flow
        flow_config = self.project_config.get_flow(flow_name)
        flow = FlowCoordinator(self.project_config, flow_config, name=flow_name)
        return [
            {
                "name": step.task_name,
                "is_required": True,
                "path": step.path,
                "step_num": str(step.step_num),
                "task_class": ".".join(
                    [step.task_class.__module__, step.task_class.__name__]
                ),
                "task_config": json.dumps(step.task_config),
                # @@@ `kind`
            }
            for step in flow.steps
        ]
        # @@@ Decompose update_dependencies/deploy_pre/deploy_post
