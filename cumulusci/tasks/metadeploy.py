import json
from pathlib import Path
from zipfile import ZipFile

import requests

from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.github import get_tag_by_name
from cumulusci.core.metadeploy.api import MetaDeployAPI
from cumulusci.core.metadeploy.labels import (
    METADEPLOY_DIR,
    read_default_labels,
    read_label_files,
    save_default_labels,
    update_step_labels,
)
from cumulusci.core.metadeploy.models import (
    FrozenStep,
    MetaDeployPlan,
    PlanTemplate,
    Product,
    Version,
)
from cumulusci.core.metadeploy.plans import get_frozen_steps
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_bool_arg
from cumulusci.utils import download_extract_github, temporary_dir
from cumulusci.utils.http.requests_utils import safe_json_from_response
from cumulusci.utils.yaml.cumulusci_yml import Plan


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
        self.commit: str = self.options.get("commit")
        if not self.tag and not self.commit:
            raise TaskOptionsError("You must specify either the tag or commit option.")
        self.labels_path = self.options.get("labels_path", METADEPLOY_DIR)
        Path(self.labels_path).mkdir(parents=True, exist_ok=True)

        if plan_name := self.options.get("plan"):
            self.plan_configs = {
                plan_name: self.project_config.lookup(f"plans__{plan_name}")
            }
        else:
            self.plan_configs = self.project_config.plans

        self.labels = read_default_labels(self.labels_path)

    def _run_task(self):
        repo_owner = self.project_config.repo_owner
        repo_name = self.project_config.repo_name
        repo_url = f"https://github.com/{repo_owner}/{repo_name}"

        # Find or create Version
        product = self._find_product(repo_url)

        if not self.dry_run:
            version = self._find_or_create_version(product)
            if self.labels_path and "slug" in product:
                self._publish_labels(product.slug)

        zf: ZipFile = self._checkout_tag(repo_owner, repo_name)
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
                steps = self._freeze_steps(project_config, plan_config)
                plan: MetaDeployPlan = MetaDeployPlan.parse_obj(
                    dict(plan_config, steps=steps)
                )
                self.labels.update(plan.get_labels())

                if not self.dry_run:
                    self._publish_plan(product, version, plan_name, plan_config, steps)

            # Update version to set is_listed=True
            if self.publish:
                self.api.update_version(version.id)
                self.logger.info(f"Published Version {version.url}")

        # Save labels
        self.logger.info(f"Updating labels in {self.labels_path}")
        save_default_labels(self.labels_path, self.labels)

    def _checkout_tag(self, repo_owner, repo_name) -> ZipFile:
        # Check out the specified tag
        gh = self.project_config.get_github_api()
        repo = gh.repository(repo_owner, repo_name)
        if self.tag:
            tag = get_tag_by_name(repo, self.tag)
            self.commit = tag.object.sha
        self.logger.info(
            f"Downloading commit {self.commit} of {repo.full_name} from GitHub"
        )
        return download_extract_github(gh, repo_owner, repo_name, ref=self.commit)

    def _freeze_steps(self, project_config, plan_config) -> list:
        steps = get_frozen_steps(project_config, plan_config)
        self.logger.debug("Prepared steps:\n" + json.dumps(steps, indent=4))

        steps = [FrozenStep.parse_obj(step) for step in steps]
        update_step_labels(steps, self.labels)
        return steps

    def _publish_plan(self, product, version, plan_name, plan_config, steps):
        plan_template = self._find_or_create_plan_template(
            product, plan_name, plan_config
        )

        parsed_plan = Plan.parse_obj(self.project_config.config["plans"][plan_name])
        plan_json = MetaDeployPlan(
            plan_template=plan_template.url,
            is_listed=parsed_plan.is_listed,
            post_install_message=plan_config.get("post_install_message", ""),
            preflight_message=plan_config.get("post_install_message", ""),
            tier=parsed_plan.tier,
            title=parsed_plan.title,
            steps=steps,
            supported_orgs=parsed_plan.allowed_org_providers,
            version=version.url,
            # Use same AllowedList as the product, if any
            visible_to=product.visible_to,
            preflight_checks=plan_config.get("checks"),
        )

        # Create Plan
        plan = self.api.create_plan(plan=plan_json)
        self.logger.info(f"Created Plan {plan.url}")

    def _find_product(self, repo_url) -> Product:
        product: Product = self.api.find_product(repo_url)
        self.labels["product"].update(product.get_labels())
        return product

    def _find_or_create_version(self, product):
        """Create a Version in MetaDeploy if it doesn't already exist"""
        label: str = self._get_label()

        version_to_create = Version(
            product=product.url,
            label=label,
            is_production=True,
            commit_ish=self.tag or self.commit,
            is_listed=False,
        )
        version: Version = self.api.find_or_create_version(
            product.id, version_to_create
        )

        self.logger.info(f"Found or created {version.url}")
        return version

    def _get_label(self) -> str:
        if self.tag:
            return self.project_config.get_version_for_tag(self.tag)
        else:
            return self.commit

    def _find_or_create_plan_template(self, product, plan_name, plan_config):
        template_to_create: PlanTemplate = PlanTemplate(
            name=plan_name,
            product=product.url,
            preflight_message=plan_config.get("preflight_message", ""),
            post_install_message=plan_config.get("post_install_message", ""),
            error_message=plan_config.get("error_message", ""),
        )

        plantemplate: PlanTemplate = self.api.find_or_create_plan_template(
            product.id, template_to_create, plan_config["slug"]
        )
        self.logger.info(f"Found or created {plantemplate.url}")
        return plantemplate

    def _publish_labels(self, slug):
        """Publish labels in all languages to MetaDeploy."""
        for lang, label in read_label_files(self.labels_path, slug).items():
            self.logger.info(f"Updating {lang} translations")
            try:
                self.api.update_lang_translation(lang, label)
            except requests.exceptions.HTTPError as err:
                self.logger.warning(f"Could not update {lang} translation: {err}")
