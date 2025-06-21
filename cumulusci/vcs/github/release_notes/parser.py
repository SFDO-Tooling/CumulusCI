import logging
import re
from typing import Dict

import github3.exceptions

from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.core.versions import PackageVersionNumber
from cumulusci.tasks.release_notes.parser import ChangeNotesLinesParser, IssuesParser
from cumulusci.utils.yaml.cumulusci_yml import ReleaseNotesParser


def parser_configs(project_config: BaseProjectConfig) -> Dict[int, ReleaseNotesParser]:
    configs = (
        project_config.project__git__release_notes__parsers__github.values()
        if project_config.project__git__release_notes__parsers__github
        else {}
    )
    configs = (
        project_config.project__git__release_notes__parsers.values()
        if not configs and project_config.project__git__release_notes__parsers
        else configs
    )
    return configs


class GithubLinesParser(ChangeNotesLinesParser):
    def __init__(self, release_notes_generator, title):
        super(GithubLinesParser, self).__init__(release_notes_generator, title)
        self.link_pr = release_notes_generator.link_pr
        self.pr_number = None
        self.pr_url = None

    def _process_change_note(self, pull_request):
        self.pr_number = pull_request.number
        self.pr_url = pull_request.html_url
        return pull_request.body

    def _add_link(self, line):
        if self.link_pr:
            line += " [[PR{}]({})]".format(self.pr_number, self.pr_url)
        return line


class GithubIssuesParser(IssuesParser):
    ISSUE_COMMENT = {
        "beta": "Included in beta release",
        "prod": "Included in production release",
    }

    def __new__(cls, release_notes_generator, title, issue_regex=None):
        if not release_notes_generator.has_issues:
            logging.getLogger(__file__).warning(
                "Issues are disabled for this repository. Falling back to change notes parser."
            )
            return GithubLinesParser(release_notes_generator, title)

        return super().__new__(cls)

    def __init__(self, release_notes_generator, title, issue_regex=None):
        super().__init__(release_notes_generator, title, issue_regex)
        self.link_pr = release_notes_generator.link_pr
        self.pr_number = None
        self.pr_url = None
        self.publish = release_notes_generator.do_publish
        self.github = release_notes_generator.github

    def _add_line(self, line):
        # find issue numbers per line
        issue_numbers = re.findall(self.issue_regex, line, flags=re.IGNORECASE)
        for issue_number in issue_numbers:
            self.content.append(
                {
                    "issue_number": int(issue_number),
                    "pr_number": self.pr_number,
                    "pr_url": self.pr_url,
                }
            )

    def _get_default_regex(self):
        keywords = (
            "close",
            "closes",
            "closed",
            "fix",
            "fixes",
            "fixed",
            "resolve",
            "resolves",
            "resolved",
        )
        return r"(?:{})\s\[?#(\d+)\]?".format("|".join(keywords))

    def _render_content(self):
        content = []
        for item in sorted(self.content, key=lambda k: k["issue_number"]):
            issue = self._get_issue(item["issue_number"])
            txt = "#{}: {}".format(item["issue_number"], issue.title)
            if self.link_pr:
                txt += " [[PR{}]({})]".format(item["pr_number"], item["pr_url"])
            content.append(txt)
            if self.publish:
                self._add_issue_comment(issue)
        return "\r\n".join(content)

    def _get_issue(self, issue_number):
        try:
            issue = self.github.issue(
                self.release_notes_generator.github_info["github_owner"],
                self.release_notes_generator.github_info["github_repo"],
                issue_number,
            )
        except github3.exceptions.NotFoundError:
            raise GithubApiNotFoundError("Issue #{} not found".format(issue_number))
        return issue

    def _process_change_note(self, pull_request):
        self.pr_number = pull_request.number
        self.pr_url = pull_request.html_url
        return pull_request.body

    def _add_issue_comment(self, issue):
        # Ensure all issues have a comment on which release they were fixed
        prefix_beta = self.release_notes_generator.github_info["prefix_beta"]
        prefix_prod = self.release_notes_generator.github_info["prefix_prod"]

        # ParentPullRequestNotesGenerator doesn't utilize a current_tag
        if not hasattr(self.release_notes_generator, "current_tag"):
            return
        elif self.release_notes_generator.current_tag.startswith(prefix_beta):
            is_beta = True
        elif self.release_notes_generator.current_tag.startswith(prefix_prod):
            is_beta = False
        else:
            # not production or beta tag, don't comment
            return
        if is_beta:
            comment_prefix = self.ISSUE_COMMENT["beta"]
        else:
            comment_prefix = self.ISSUE_COMMENT["prod"]
        version_str = PackageVersionNumber.parse_tag(
            self.release_notes_generator.current_tag, prefix_beta, prefix_prod
        ).format()
        has_comment = False
        for comment in issue.comments():
            if comment.body.startswith(comment_prefix):
                has_comment = True
                break
        if not has_comment:
            issue.create_comment("{} {}".format(comment_prefix, version_str))
