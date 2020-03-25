import cumulusci
import datetime
import jinja2
import os
from cumulusci.tasks.github.base import BaseGithubTask


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
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.template = self.options.get("template") or os.path.join(
            cumulusci.__location__, "tasks", "qar", "templates", "github.html",
        )
        repos = self.options.get("repos")
        self.repos = repos.split(",") if repos else None

    def _run_task(self):
        org = self.github.organization(self.options["organization"])
        org_members = {}
        repos = {}
        teams = {}

        self.logger.info("Fetching members...")
        for member in org.members(role="admin"):
            org_members[member.login] = {
                "obj": member,
                "admin": True,
            }

        for member in org.members(role="member"):
            org_members[member.login] = {
                "obj": member,
                "admin": False,
            }

        self.logger.info("Fetching teams...")
        for team in org.teams():
            teams[team.name] = {
                "obj": team,
                "members": {},
                "repos": {},
            }
            members = {}
            for member in team.members():
                info = {
                    "user": member,
                    "role": None,
                }
                teams[team.name]["members"][member.login] = info
            for member in team.members(role="maintainer"):
                teams[team.name]["members"][member.login]["role"] = "maintainer"
            for member in team.members(role="member"):
                teams[team.name]["members"][member.login]["role"] = "member"
            for repo in team.repositories():
                info = {
                    "repo": repo,
                    "read": True,  # All teams returned at least have read
                    "write": repo.permissions["push"] is True
                    or repo.permissions["admin"] is True,
                    "admin": repo.permissions["admin"] is True,
                }
                teams[team.name]["repos"][repo.name] = info

        self.logger.info("Fetching repos...")
        for repo in org.repositories():
            if self.repos and repo.name not in self.repos:
                self.logger.warning(f"Skipping {repo.name}")
                continue
            repos[repo.name] = {
                "obj": repo,
                "users": {},
                "users_direct": {},
                "teams": {},
            }

            for user in repo.collaborators():
                info = {
                    "user": user,
                    "read": True,  # All collaborators at least have read
                    "write": user.permissions["push"] is True
                    or user.permissions["admin"] is True,
                    "admin": user.permissions["admin"] is True,
                    "is_member": user.login in members,
                }
                # If this is a public repo, ignore read only users
                if (
                    repo.private is False
                    and info["write"] is False
                    and info["admin"] is False
                ):
                    continue

                # Skip org members whose only perms come from org membership
                if repo.private is True and user.login in members:
                    if (
                        org.default_repository_permission == "write"
                        and info["write"] is True
                        and info["admin"] is False
                    ):
                        continue
                    elif (
                        org.default_repository_pemrission == "read"
                        and info["write"] is False
                        and info["admin"] is False
                    ):
                        continue

                repos[repo.name]["users"][user.login] = info

            for team in repo.teams():
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
                for team_name, team_info in repos[repo.name]["teams"].items():
                    team = teams.get(team_name)
                    if not team:
                        self.logger.warning(f"Cannot see team {team_name}")
                        continue
                    if username in ["members"]:
                        if user_info["admin"] is True and team_info["admin"] is True:
                            from_team = True
                            break
                        elif user_info["write"] is True and team_info["write"] is True:
                            from_team = True
                            break
                        elif user_info["read"] == team_info["read"]:
                            from_team = True
                            break
                if from_team is False:
                    repos[repo.name]["users_direct"][username] = user_info

        self.logger.info("Writing report to {output}".format(**self.options))
        with open(self.template, "r") as f:
            template = jinja2.Template(f.read())

        with open(self.options["output"], "w") as f:
            f.write(
                template.render(
                    org_members=org_members,
                    repos=repos,
                    teams=teams,
                    org=org,
                    now=datetime.datetime.now(),
                    check=lambda x: "&#x2713;" if x else "",
                )
            )
