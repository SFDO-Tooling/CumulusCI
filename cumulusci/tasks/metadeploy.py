import json
import requests

from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.tasks import BaseTask
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.utils import download_extract_github
from cumulusci.utils import temporary_dir


class BaseMetaDeployTask(BaseTask):
    """Base class for tasks that talk to MetaDeploy's API."""

    def _init_task(self):
        metadeploy_service = self.project_config.keychain.get_service("metadeploy")
        self.base_url = metadeploy_service.url
        self.api = requests.Session()
        self.api.headers["Authorization"] = "token {}".format(metadeploy_service.token)

    def _call_api(self, method, path, collect_pages=False, **kwargs):
        next_url = self.base_url + path
        results = []
        while next_url is not None:
            response = self.api.request(method, next_url, **kwargs)
            if response.status_code == 400:
                raise requests.exceptions.HTTPError(response.content)
            response.raise_for_status()
            response = response.json()
            if "links" in response and collect_pages:
                results.extend(response["data"])
                next_url = response["links"]["next"]
            else:
                return response
        return results


class Publish(BaseMetaDeployTask):
    """Publishes installation plans to MetaDeploy.
    """

    task_options = {
        "tag": {"description": "Name of the git tag to publish", "required": True},
        "plan": {
            "description": "Name of the plan(s) to publish. "
            "This refers to the `plans` section of cumulusci.yml. "
            "By default, all plans will be published.",
            "required": False,
        },
        "dry_run": {
            "description": "If True, print steps without publishing.",
            "required": False,
        },
    }

    def _init_task(self):
        super(Publish, self)._init_task()
        self.dry_run = self.options.get("dry_run")

        plan_name = self.options.get("plan")
        if plan_name:
            plan_configs = {}
            plan_configs[plan_name] = getattr(
                self.project_config, "plans__{}".format(plan_name)
            )
            self.plan_configs = plan_configs
        else:
            self.plan_configs = self.project_config.plans

    def _run_task(self):
        # Find or create Version
        if not self.dry_run:
            product = self._find_product()
            version = self._find_or_create_version(product)

        # Check out the specified tag
        repo_owner = self.project_config.repo_owner
        repo_name = self.project_config.repo_name
        gh = self.project_config.get_github_api()
        repo = gh.repository(repo_owner, repo_name)
        tag = self.options["tag"]
        commit_sha = repo.tag(repo.ref("tags/" + tag).object.sha).object.sha
        self.logger.info(
            "Downloading commit {} of {} from GitHub".format(commit_sha, repo.full_name)
        )
        zf = download_extract_github(gh, repo_owner, repo_name, ref=commit_sha)
        with temporary_dir() as project_dir:
            zf.extractall(project_dir)
            project_config = BaseProjectConfig(
                self.project_config.global_config_obj,
                repo_info={
                    "root": project_dir,
                    "owner": repo_owner,
                    "name": repo_name,
                    "url": self.project_config.repo_url,
                    "branch": tag,
                    "commit": commit_sha,
                },
            )
            project_config.set_keychain(self.project_config.keychain)

            # Create each plan
            for plan_name, plan_config in self.plan_configs.items():
                steps = self._freeze_steps(project_config, plan_config)
                self.logger.debug("Prepared steps:\n" + json.dumps(steps, indent=4))
                if not self.dry_run:
                    self._publish_plan(product, version, plan_name, plan_config, steps)

            # Update version to set is_listed=True
            if not self.dry_run:
                self._call_api(
                    "PATCH",
                    "/versions/{}".format(version["id"]),
                    json={"is_listed": True},
                )
                self.logger.info("Published Version {}".format(version["url"]))

    def _publish_plan(self, product, version, plan_name, plan_config, steps):
        plan_template = self._find_or_create_plan_template(
            product, plan_name, plan_config
        )

        plan_json = {
            "is_listed": plan_config.get("is_listed", True),
            "plan_template": plan_template["url"],
            "post_install_message_additional": plan_config.get(
                "post_install_message_additional", ""
            ),
            "preflight_message_additional": plan_config.get(
                "preflight_message_additional", ""
            ),
            "steps": steps,
            "tier": plan_config["tier"],
            "title": plan_config["title"],
            "version": version["url"],
            # Use same AllowedList as the product, if any
            "visible_to": product.get("visible_to"),
        }
        if plan_config.get("checks"):
            plan_json["preflight_checks"] = plan_config["checks"]

        # Create Plan
        plan = self._call_api("POST", "/plans", json=plan_json)
        self.logger.info("Created Plan {}".format(plan["url"]))

    def _freeze_steps(self, project_config, plan_config):
        steps = plan_config["steps"]
        flow_config = FlowConfig(plan_config)
        flow = FlowCoordinator(project_config, flow_config)
        steps = []
        for step in flow.steps:
            task = step.task_class(
                project_config, TaskConfig(step.task_config), name=step.task_name
            )
            steps.extend(task.freeze(step))
        return steps

    def _find_product(self):
        repo_url = self.project_config.project__git__repo_url
        result = self._call_api("GET", "/products", params={"repo_url": repo_url})
        if len(result["data"]) != 1:
            raise Exception(
                "No product found in MetaDeploy with repo URL {}".format(repo_url)
            )
        return result["data"][0]

    def _find_or_create_version(self, product):
        """Create a Version in MetaDeploy if it doesn't already exist
        """
        tag = self.options["tag"]

        label = self.project_config.get_version_for_tag(tag)
        result = self._call_api(
            "GET", "/versions", params={"product": product["id"], "label": label}
        )
        if len(result["data"]) == 0:
            version = self._call_api(
                "POST",
                "/versions",
                json={
                    "product": product["url"],
                    "label": label,
                    "description": self.options.get("description", ""),
                    "is_production": True,
                    "commit_ish": tag,
                    "is_listed": False,
                },
            )
            self.logger.info("Created {}".format(version["url"]))
        else:
            version = result["data"][0]
            self.logger.info("Found {}".format(version["url"]))
        return version

    def _find_or_create_plan_template(self, product, plan_name, plan_config):
        result = self._call_api(
            "GET",
            "/plantemplates",
            params={"product": product["id"], "name": plan_name},
        )
        if len(result["data"]) == 0:
            plantemplate = self._call_api(
                "POST",
                "/plantemplates",
                json={"name": plan_name, "product": product["url"]},
            )
            self.logger.info("Created {}".format(plantemplate["url"]))
            planslug = self._call_api(
                "POST",
                "/planslug",
                json={"slug": plan_config["slug"], "parent": plantemplate["url"]},
            )
            self.logger.info("Created {}".format(planslug["url"]))
        else:
            plantemplate = result["data"][0]
            self.logger.info("Found {}".format(plantemplate["url"]))
        return plantemplate
