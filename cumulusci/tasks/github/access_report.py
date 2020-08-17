from typing import Set
import datetime
import os
import csv
from itertools import chain
from pathlib import Path
import subprocess

from jinja2 import Environment, FileSystemLoader

from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.core.utils import process_list_arg
from cumulusci.core.exceptions import TaskOptionsError


class OrganizationReport(BaseGithubTask):
    task_options = {
        "organization": {
            "description": "The name of the Github organization",
            "required": True,
        },
        "output": {
            "description": "The file where the report should be generated",
            "required": True,
        },
        "template": {
            "description": "The path to a custom jinja2 template file for rendering the report",
        },
        "repos": {
            "description": "A comma-separated list of Repo names to report for (not including org-name)",
        },
        "additional_info_csv": {
            "description": "The path to a CSV file. "
            "The CSV must have column headings in the first row. "
            "One of the column headings must be 'Github Username'. "
            "The other columns will be added to the Member report."
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        default_template = (
            Path(__file__).parent / "report_templates/github_access_report.html"
        )
        template = self.options.get("template", default_template)
        self.template = Path(template)

        if not self.template.is_file():
            raise TaskOptionsError(f"{self.template} is not a file")

        repos = self.options.get("repos")
        self.repos = set(process_list_arg(repos)) if repos else None
        self.additional_info_csv = self.options.get("additional_info_csv")

    def _run_task(self):
        org = self.github.organization(self.options["organization"])
        if self.additional_info_csv:
            member_extra_info = self._parse_member_extra_info(self.additional_info_csv)
            extra_fields = list(next(iter(member_extra_info.values())).keys())[1:]
        else:
            member_extra_info = {}
            extra_fields = {}

        org_members = self._fetch_members(org, member_extra_info)
        teams, ignored_teams = self._fetch_teams(org, self.repos)
        repos, ignored_repos = self._fetch_repos(org, org_members, teams)
        org_members, ignored_org_members = self._filter_org_members(org_members, repos)
        ignored = {
            "teams": ignored_teams,
            "users": ignored_org_members,
            "repos": ignored_repos,
        }
        self._report(org, org_members, teams, repos, extra_fields, ignored)

    def _filter_org_members(self, org_members, repos):
        flatten = chain.from_iterable

        relevant_org_members = set(
            flatten(repo["users"].keys() for repo in repos.values())
        )
        rc = {
            member: org_members[member]
            for member in sorted(org_members.keys(), key=lambda x: x.lower())
            if member in set(relevant_org_members)
        }
        ignored = set(org_members) - relevant_org_members

        return sorted_dict(rc), sorted(list(ignored), key=lambda x: x.lower())

    def _parse_member_extra_info(self, additional_info_csv):
        with open(additional_info_csv) as f:
            dict_reader = csv.DictReader(f)
            return {row["Github Username"]: row for row in dict_reader}

    def _fetch_members(self, org, member_extra_info):
        self.logger.info("Fetching members...")
        org_members = {}

        def member_dict(member, admin):
            extra_info = member_extra_info.get(member.login) or {}
            return {
                "obj": member,
                "admin": admin,
                "email": self.github.user(member.login).email,
                **extra_info,
            }

        for member in org.members(role="admin"):
            org_members[member.login] = member_dict(member, True)

        for member in org.members(role="member"):
            org_members[member.login] = member_dict(member, False)

        return sorted_dict(org_members)

    def _fetch_teams(self, org, relevant_repos: Set[str]):
        teams = {}
        ignored = set()
        self.logger.info("Fetching teams...")
        for team in org.teams():
            repos = team.repositories()
            repo_names = set(repo.name for repo in repos)
            if relevant_repos and not (set(relevant_repos) & set(repo_names)):
                self.logger.info(
                    f"Skipping Team '{team.name}' because they do not have access to relevant repos"
                )
                ignored.add(team.name)
                continue
            teams[team.name] = {
                "obj": team,
                "members": {},
                "repos": {},
            }
            for member in sorted(team.members(), key=lambda u: u.login.lower()):
                info = {
                    "user": member,
                    "maintainer": False,
                }
                teams[team.name]["members"][member.login] = info
            for member in team.members(role="maintainer"):
                teams[team.name]["members"][member.login]["maintainer"] = True
            for repo in sorted(repos, key=lambda repo: repo.name.lower()):
                if relevant_repos and repo.name not in relevant_repos:
                    continue
                info = {
                    "repo": repo,
                    "read": True,  # All teams returned at least have read
                    "write": repo.permissions["push"] is True
                    or repo.permissions["admin"] is True,
                    "admin": repo.permissions["admin"] is True,
                }
                teams[team.name]["repos"][repo.name] = info
        return sorted_dict(teams), sorted(list(ignored))

    def _fetch_repos(self, org, org_members, teams):
        repos = {}
        ignored = set()
        org_owners = set(member.login for member in org.members(role="admin"))
        for repo in sorted(org.repositories(), key=lambda repo: repo.name.lower()):
            if self.repos and repo.name not in self.repos:
                self.logger.info(f"Skipping Repo '{repo.name}''")
                ignored.add(repo.name)
                continue
            repos[repo.name] = {
                "obj": repo,
                "users": {},
                "users_direct": {},
                "teams": {},
            }

            for user in sorted(repo.collaborators(), key=lambda u: u.login.lower()):
                info = {
                    "user": user,
                    "read": True,  # All collaborators at least have read
                    "write": user.permissions["push"] is True
                    or user.permissions["admin"] is True,
                    "admin": user.permissions["admin"] is True,
                    "is_member": user.login in org_members,
                }
                # If this is a public repo, ignore read only users
                if (
                    repo.private is False
                    and info["write"] is False
                    and info["admin"] is False
                ):
                    continue

                # Skip org members whose only perms come from org membership
                if repo.private is True and user.login in org_members:
                    if (
                        org.default_repository_permission == "write"
                        and info["write"] is True
                        and info["admin"] is False
                    ):
                        continue
                    elif (
                        org.default_repository_permission == "read"
                        and info["write"] is False
                        and info["admin"] is False
                    ):
                        continue

                repos[repo.name]["users"][user.login] = info

            for team in sorted(repo.teams(), key=lambda x: x.name.lower()):
                # Skip teams from another org which can happen when a repo is moved to a different org
                if "/{}/".format(org.id) not in team.url:
                    continue
                info = {
                    "team": team,
                    "read": True,  # All teams at least have read
                    "write": team.permission in ["push", "admin"],
                    "admin": team.permission == "admin",
                }
                repos[repo.name]["teams"][team.name] = info

            for username, user_info in repos[repo.name]["users"].items():
                from_team = False
                for value in [
                    user_info["admin"],
                    user_info["write"],
                    user_info["read"],
                ]:
                    assert isinstance(value, bool)
                for team_name, team_info in sorted_dict(
                    repos[repo.name]["teams"]
                ).items():
                    team = teams.get(team_name)
                    if not team:
                        self.logger.warning(f"Cannot see team {team_name}")
                        continue
                    if username in team["members"]:
                        for value in [
                            team_info["admin"],
                            team_info["write"],
                            team_info["read"],
                        ]:
                            assert isinstance(value, bool)

                        # do not rewrite these as "ands".
                        # "ands" work correctly for triggering the from_team
                        # but it will send you down the wrong "elif" when multiple
                        # user_info fields are true
                        if user_info["admin"]:
                            if team_info["admin"] is True:
                                from_team = True
                                break
                        elif user_info["write"]:
                            if team_info["write"] is True:
                                from_team = True
                                break
                        elif user_info["read"]:
                            if team_info["read"] is True:
                                from_team = True
                                break
                if from_team is False and username not in org_owners:
                    repos[repo.name]["users_direct"][username] = user_info

        return sorted_dict(repos), sorted(list(ignored), key=lambda x: x.lower())

    def _report(self, org, org_members, teams, repos, extra_fields, ignored):
        self.logger.info("Writing report to {output}".format(**self.options))

        loader_dir = str(self.template.parent)
        environment = RelEnvironment(loader=FileSystemLoader(loader_dir))
        template = environment.get_template(self.template.name)
        url, mode = script_url(self.project_config)

        with open(self.options["output"], "w") as f:
            f.write(
                template.render(
                    org_members=sorted_dict(org_members),
                    repos=sorted_dict(repos),
                    teams=sorted_dict(teams),
                    org=org,
                    now=datetime.datetime.now(),
                    check=lambda x: "&#x2713;" if x else "",
                    commit=self.project_config.repo_commit,
                    extra_fields=extra_fields,
                    ignored=ignored,
                    link_style=False,  # change this for rapid changing of the CSS
                    script_url=url,
                    mode=mode,
                )
            )


def get_commit():
    first_line = subprocess.check_output(["git", "show"]).decode("utf-8").split("\n")[0]
    commit = first_line.split()[1]
    return commit


def script_url(project_config):
    proj = project_config
    diff = subprocess.check_output(["git", "diff"]).decode("utf-8").strip()
    commit = proj.commit or get_commit()
    mode = "dev" if diff else "prod"
    if mode == "dev":
        print("Warning: Running in dev mode because github repo is dirty.")
    relpath = proj.relpath(__file__)

    url = f"https://{repo_url(project_config)}/blob/{commit}/{relpath}"
    return url, mode


def repo_url(project_config):
    return project_config.repo_url.split("@")[-1].rsplit(".", 1)[0].replace(":", "/")


class RelEnvironment(Environment):
    """Override join_path() to enable relative template paths.

    Per: https://stackoverflow.com/a/3655911/113477"""

    def join_path(self, template, parent):
        return os.path.join(os.path.dirname(parent), template)


def sorted_dict(d):
    return {
        k: v for (k, v) in sorted(d.items(), key=lambda k_v_pair: k_v_pair[0].lower())
    }
