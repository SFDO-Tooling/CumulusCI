import contextlib
import json
import re
from pathlib import Path
from typing import List, Optional, Union

import requests

from cumulusci.core.config import BaseProjectConfig, FlowConfig, TaskConfig
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.core.github import get_tag_by_name
from cumulusci.core.metadeploy.api import MetaDeployAPI
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_bool_arg
from cumulusci.utils import cd, download_extract_github, temporary_dir
from cumulusci.utils.http.requests_utils import safe_json_from_response
from cumulusci.utils.yaml.cumulusci_yml import Plan

INSTALL_VERSION_RE = re.compile(r"^Install .*\d$")


class BaseMetaDeployTask(BaseTask):
    """Base class for tasks that talk to MetaDeploy's API."""

    def _init_task(self):
        metadeploy_service = self.project_config.keychain.get_service("metadeploy")
        self.api: MetaDeployAPI = MetaDeployAPI(metadeploy_service)

    def _call_api(self, method, path, collect_pages=False, **kwargs):
        next_url = path
        results = []
        while next_url is not None:
            response = self.api.session.request(method, next_url, **kwargs)
            if response.status_code == 400:
                raise requests.exceptions.HTTPError(response.content)
            response = safe_json_from_response(response)
            if "links" in response and collect_pages:
                results.extend(response["data"])
                next_url = response["links"]["next"]
            else:
                return response
        return results


class Publish(BaseMetaDeployTask):
    """Publishes installation plans to MetaDeploy."""

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
        self.dry_run = process_bool_arg(self.options.get("dry_run") or False)
        self.publish = not self.dry_run and process_bool_arg(
            self.options.get("publish") or False
        )
        self.tag = self.options.get("tag")
        self.commit = self.options.get("commit")
        if not self.tag and not self.commit:
            raise TaskOptionsError("You must specify either the tag or commit option.")
        self.labels_path = self.options.get("labels_path", "metadeploy")
        Path(self.labels_path).mkdir(parents=True, exist_ok=True)

        if plan_name := self.options.get("plan"):
            plan_configs = {
                plan_name: self.project_config.lookup(f"plans__{plan_name}")
            }
            self.plan_configs = plan_configs
        else:
            self.plan_configs = self.project_config.plans

        self._load_labels()

    def _run_task(self):
        repo_owner = self.project_config.repo_owner
        repo_name = self.project_config.repo_name
        repo_url = f"https://github.com/{repo_owner}/{repo_name}"

        # Find or create Version
        product = self._find_product(repo_url)
        if not product:
            raise CumulusCIException(
                f"No product found in MetaDeploy with repo URL {repo_url}"
            )
        if not self.dry_run:
            version = self._find_or_create_version(product)
            if self.labels_path and "slug" in product:
                self._publish_labels(product["slug"])

        # Check out the specified tag
        gh = self.project_config.get_github_api()
        repo = gh.repository(repo_owner, repo_name)
        if self.tag:
            tag = get_tag_by_name(repo, self.tag)
            self.commit = tag.object.sha
        self.logger.info(
            f"Downloading commit {self.commit} of {repo.full_name} from GitHub"
        )
        zf = download_extract_github(gh, repo_owner, repo_name, ref=self.commit)
        with temporary_dir() as project_dir:
            zf.extractall(project_dir)
            project_config = BaseProjectConfig(
                self.project_config.universal_config_obj,
                repo_info={
                    "root": project_dir,
                    "owner": repo_owner,
                    "name": repo_name,
                    "url": repo_url,
                    "branch": self.tag or self.commit,
                    "commit": self.commit,
                },
            )
            project_config.set_keychain(self.project_config.keychain)

            # Create each plan
            for plan_name, plan_config in self.plan_configs.items():
                self._add_plan_labels(
                    plan_name=plan_name,
                    plan_config=plan_config,
                )

                steps = self._freeze_steps(project_config, plan_config)

                if not self.dry_run:
                    self._publish_plan(product, version, plan_name, plan_config, steps)

            # Update version to set is_listed=True
            if self.publish:
                self.api.update_version(version["id"])
                self.logger.info(f"Published Version {version['url']}")

        # Save labels
        self._save_labels()

    def _freeze_steps(self, project_config, plan_config) -> list:
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
        self.logger.debug("Prepared steps:\n" + json.dumps(steps, indent=4))

        self._add_step_labels(steps)
        return steps

    def _add_plan_labels(self, plan_name, plan_config) -> None:
        """Add labels for plans, steps, and checks."""
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
        self._add_check_labels(plan_config)

    def _add_step_labels(self, steps) -> None:
        for step in steps:
            # avoid separate labels for installing each package
            if INSTALL_VERSION_RE.match(step["name"]):
                self._add_label(
                    "steps",
                    "Install {product} {version}",
                    "title of installation step",
                )
            else:
                self._add_label("steps", step["name"], "title of installation step")
            self._add_label(
                "steps",
                step.get("description"),
                "description of installation step",
            )
            self._add_check_labels(step["task_config"])

    def _add_check_labels(self, config) -> None:
        for check in config.get("checks", []):
            self._add_label("checks", check.get("message"), "shown if validation fails")

    def _publish_plan(self, product, version, plan_name, plan_config, steps):
        plan_template = self._find_or_create_plan_template(
            product, plan_name, plan_config
        )

        allowed_org_providers = self._get_allowed_org_providers(plan_name)
        supported_orgs = self._convert_org_providers_to_plan_equivalent(
            allowed_org_providers
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
            "supported_orgs": supported_orgs,
            "tier": plan_config["tier"],
            "title": plan_config["title"],
            "version": version["url"],
            # Use same AllowedList as the product, if any
            "visible_to": product.get("visible_to"),
        }
        if plan_config.get("checks"):
            plan_json["preflight_checks"] = plan_config["checks"]

        # Create Plan
        plan = self.api.create_plan(plan=plan_json)
        self.logger.info(f"Created Plan {plan['url']}")

    def _get_allowed_org_providers(self, plan_name: str) -> List[str]:
        "Validates and returns the org providers for a given plan"
        plan = Plan.parse_obj(self.project_config.config["plans"][plan_name])
        return plan.allowed_org_providers

    def _convert_org_providers_to_plan_equivalent(
        self, providers: Union[None, List[str]]
    ) -> str:
        """Given a list of plan.allowed_org_providers return the value that
        corresponds `supported_orgs` field on the Plan model in MetaDeploy
        """
        if not providers or providers == ["user"]:
            org_providers = "Persistent"
        elif "user" in providers and "devhub" in providers:
            org_providers = "Both"
        elif providers == ["devhub"]:
            org_providers = "Scratch"

        return org_providers

    def _find_product(self, repo_url):
        product = self.api.find_product(repo_url)
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
        """Create a Version in MetaDeploy if it doesn't already exist"""
        if self.tag:
            label = self.project_config.get_version_for_tag(self.tag)
        else:
            label = self.commit

        version: Optional[dict] = self.api.find_version(
            query={"product": product["id"], "label": label}
        )
        verb: str = "Found" if version else "Created"

        if not version:
            version_dict = {
                "product": product["url"],
                "label": label,
                "description": self.options.get("description", ""),
                "is_production": True,
                "commit_ish": self.tag or self.commit,
                "is_listed": False,
            }
            version = self.api.create_version(version_dict)

        self.logger.info(f"{verb} {version['url']}")
        return version

    def _find_or_create_plan_template(self, product, plan_name, plan_config):
        plantemplate = self.api.find_plan_template(
            {"product": product["id"], "name": plan_name}
        )
        verb: str = "Found" if plantemplate else "Created"

        if not plantemplate:
            plantemplate = self.api.create_plan_template(
                {
                    "name": plan_name,
                    "product": product["url"],
                    "preflight_message": plan_config.get("preflight_message", ""),
                    "post_install_message": plan_config.get("post_install_message", ""),
                    "error_message": plan_config.get("error_message", ""),
                }
            )
            planslug = self.api.create_plan_slug(
                {"slug": plan_config["slug"], "parent": plantemplate["url"]}
            )
            self.logger.info(f"Created {planslug['url']}")
        self.logger.info(f"{verb} {plantemplate['url']}")
        return plantemplate

    def _load_labels(self):
        """Load existing English labels."""
        try:
            labels_path: Path = Path(self.labels_path, "labels_en.json")
            self.labels: dict = json.loads(labels_path.read_text())
        except FileNotFoundError:
            self.labels: dict = {}

    def _add_labels(self, obj, category, fields):
        """Add specified fields from obj to a label category."""
        for name, description in fields.items():
            if text := obj.get(name):
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
        with contextlib.suppress(FileNotFoundError):
            labels_path: Path = Path(self.labels_path, "labels_en.json")
            self.logger.info(f"Updating labels in {labels_path}")
            labels_path.write_text(json.dumps(self.labels, indent=4))

    def _publish_labels(self, slug):
        """Publish labels in all languages to MetaDeploy."""
        for path in Path(self.labels_path).glob("*.json"):
            lang = path.stem.split("_")[-1].lower()
            if lang in ("en", "en-us"):
                continue
            orig_labels = json.loads(path.read_text())
            prefixed_labels = {
                f"{slug}:{context}": labels for context, labels in orig_labels.items()
            }

            self.logger.info(f"Updating {lang} translations")
            try:
                self.api.update_lang_translation(lang, prefixed_labels)
            except requests.exceptions.HTTPError as err:
                self.logger.warning(f"Could not update {lang} translation: {err}")
