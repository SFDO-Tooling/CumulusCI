from pathlib import Path
import json
import os
import requests

from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.tasks import BaseTask
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.core.utils import process_bool_arg
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.utils import download_extract_github
from cumulusci.utils import cd
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
        "tag": {"description": "Name of the git tag to publish"},
        "commit": {"description": "Commit hash to publish"},
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
        "publish": {
            "description": "If True, set is_listed to True on the version. Default: False",
            "required": False,
        },
        "labels_path": {
            "description": "Path to a folder containing translations.",
            "required": False,
        },
    }

    def _init_task(self):
        super(Publish, self)._init_task()
        self.dry_run = self.options.get("dry_run")
        self.publish = not self.dry_run and process_bool_arg(
            self.options.get("publish", False)
        )
        self.tag = self.options.get("tag")
        self.commit = self.options.get("commit")
        if not self.tag and not self.commit:
            raise TaskOptionsError("You must specify either the tag or commit option.")
        self.labels_path = self.options.get("labels_path", "metadeploy")
        if not os.path.exists(self.labels_path):  # pragma: no cover
            os.makedirs(self.labels_path)

        plan_name = self.options.get("plan")
        if plan_name:
            plan_configs = {}
            plan_configs[plan_name] = getattr(
                self.project_config, "plans__{}".format(plan_name)
            )
            self.plan_configs = plan_configs
        else:
            self.plan_configs = self.project_config.plans

        self._load_labels()

    def _run_task(self):
        # Find or create Version
        product = self._find_product()
        if not self.dry_run:
            version = self._find_or_create_version(product)
            if self.labels_path and "slug" in product:
                self._publish_labels(product["slug"])

        # Check out the specified tag
        repo_owner = self.project_config.repo_owner
        repo_name = self.project_config.repo_name
        gh = self.project_config.get_github_api()
        repo = gh.repository(repo_owner, repo_name)
        if self.tag:
            tag = self.options["tag"]
            self.commit = repo.tag(repo.ref("tags/" + tag).object.sha).object.sha
        self.logger.info(
            "Downloading commit {} of {} from GitHub".format(
                self.commit, repo.full_name
            )
        )
        zf = download_extract_github(gh, repo_owner, repo_name, ref=self.commit)
        with temporary_dir() as project_dir:
            zf.extractall(project_dir)
            project_config = BaseProjectConfig(
                self.project_config.global_config_obj,
                repo_info={
                    "root": project_dir,
                    "owner": repo_owner,
                    "name": repo_name,
                    "url": self.project_config.repo_url,
                    "branch": self.tag or self.commit,
                    "commit": self.commit,
                },
            )
            project_config.set_keychain(self.project_config.keychain)

            # Create each plan
            for plan_name, plan_config in self.plan_configs.items():

                self._add_labels(
                    plan_config,
                    f"plan:{plan_name}",
                    {
                        "title": "title of installation plan",
                        "preflight_message": "shown before user starts installation (markdown)",
                        "preflight_message_additional": "shown before user starts installation (markdown)",
                        "post_install_message": "shown after successful installation (markdown)",
                        "post_install_message_additional": "shown after successful installation (markdown)",
                        "error_message": "shown after failed installation (markdown)",
                    },
                )
                checks = plan_config.get("checks") or []
                for check in checks:
                    self._add_label(
                        "checks", check.get("message"), "shown if validation fails"
                    )

                steps = self._freeze_steps(project_config, plan_config)
                self.logger.debug("Prepared steps:\n" + json.dumps(steps, indent=4))
                for step in steps:
                    # avoid separate labels for installing each package
                    if step["name"].startswith("Install "):
                        self._add_label(
                            "steps",
                            "Install {product} {version}",
                            "title of installation step",
                        )
                    else:
                        self._add_label(
                            "steps", step["name"], "title of installation step"
                        )
                    self._add_label(
                        "steps",
                        step.get("description"),
                        "description of installation step",
                    )
                    for check in step["task_config"].get("checks", []):
                        self._add_label(
                            "checks", check.get("message"), "shown if validation fails"
                        )

                if not self.dry_run:
                    self._publish_plan(product, version, plan_name, plan_config, steps)

            # Update version to set is_listed=True
            if self.publish:
                self._call_api(
                    "PATCH",
                    "/versions/{}".format(version["id"]),
                    json={"is_listed": True},
                )
                self.logger.info("Published Version {}".format(version["url"]))

        # Save labels
        self._save_labels()

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
        flow_config.project_config = project_config
        flow = FlowCoordinator(project_config, flow_config)
        steps = []
        for step in flow.steps:
            if step.skip:
                continue
            with cd(step.project_config.repo_root):
                task = step.task_class(
                    step.project_config,
                    TaskConfig(step.task_config),
                    name=step.task_name,
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
        product = result["data"][0]
        self._add_labels(
            product,
            "product",
            {
                "title": "name of product",
                "short_description": "tagline of product",
                "description": "shown on product detail page (markdown)",
                "click_through_agreement": "legal text shown in modal dialog",
                "error_message": "shown after failed installation (markdown)",
            },
        )
        return product

    def _find_or_create_version(self, product):
        """Create a Version in MetaDeploy if it doesn't already exist
        """
        if self.tag:
            label = self.project_config.get_version_for_tag(self.tag)
        else:
            label = self.commit
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
                    "commit_ish": self.tag or self.commit,
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
                json={
                    "name": plan_name,
                    "product": product["url"],
                    "preflight_message": plan_config.get("preflight_message", ""),
                    "post_install_message": plan_config.get("post_install_message", ""),
                    "error_message": plan_config.get("error_message", ""),
                },
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

    def _load_labels(self):
        """Load existing English labels."""
        self.labels = {}
        labels_path = os.path.join(self.labels_path, "labels_en.json")
        if os.path.exists(labels_path):
            with open(labels_path, "r") as f:
                self.labels = json.load(f)

    def _add_labels(self, obj, category, fields):
        """Add specified fields from obj to a label category."""
        for name, description in fields.items():
            text = obj.get(name)
            if text:
                if category not in self.labels:
                    self.labels[category] = {}
                label = {"message": text, "description": description}
                self.labels[category][name] = label

    def _add_label(self, category, text, description):
        """Add a single label to a label category."""
        if not text:
            return
        if category not in self.labels:
            self.labels[category] = {}
        label = {"message": text, "description": description}
        self.labels[category][text] = label

    def _save_labels(self):
        """Save updates to English labels."""
        if self.labels_path:
            labels_path = os.path.join(self.labels_path, "labels_en.json")
            self.logger.info(f"Updating labels in {labels_path}")
            with open(labels_path, "w") as f:
                json.dump(self.labels, f, indent=4)

    def _publish_labels(self, slug):
        """Publish labels in all languages to MetaDeploy."""
        for path in Path(self.labels_path).glob("*.json"):
            lang = path.stem[-2:]
            if lang == "en":
                continue
            orig_labels = json.loads(path.read_text())
            prefixed_labels = {}
            for context, labels in orig_labels.items():
                prefixed_labels[f"{slug}:{context}"] = labels
            self.logger.info(f"Updating {lang} translations")
            self._call_api("PATCH", f"/translations/{lang}", json=prefixed_labels)
