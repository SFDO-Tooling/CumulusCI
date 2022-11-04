import logging
import re
import urllib.parse

import github3.exceptions

from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.core.versions import PackageVersionNumber
from cumulusci.oauth.salesforce import PROD_LOGIN_URL, SANDBOX_LOGIN_URL


class BaseChangeNotesParser(object):
    def __init__(self, title):
        self.title = title
        self.content = []

    def parse(self):
        raise NotImplementedError()

    def render(self, existing_content=""):
        return "# {}\r\n\r\n{}".format(self.title, self._render())

    def _render(self):
        raise NotImplementedError()


class ChangeNotesLinesParser(BaseChangeNotesParser):
    def __init__(self, release_notes_generator, title):
        super(ChangeNotesLinesParser, self).__init__(title)
        self.release_notes_generator = release_notes_generator
        self.title = title
        self._in_section = False
        self.h2 = {}  # dict of h2 sections - key=header, value is list of lines
        self.h2_title = None  # has value when in h2 section

    def parse(self, change_note):
        """Returns True if a line was added to self._add_line was called, False otherwise"""
        if not self.title:
            self._in_section = True

        line_added = False
        change_note = self._process_change_note(change_note)

        if not change_note:
            return False

        for line in change_note.splitlines():
            line = self._process_line(line)

            # Look for the starting line of the section
            if self._is_start_line(line):
                self._in_section = True
                self.h2_title = None
                continue

            # Look for h2
            if line.startswith("## "):
                self.h2_title = re.sub(r"\s+#+$", "", line[3:]).lstrip()
                continue

            # Add all content once in the section
            if self._in_section:

                # End when the end of section is found
                if self._is_end_line(line):
                    self._in_section = False
                    self.h2_title = None
                    continue

                # Skip excluded lines
                if self._is_excluded_line(line):
                    continue

                self._add_line(line)
                if self.title:
                    line_added = True

        self._in_section = False
        return line_added

    def _process_change_note(self, change_note):
        # subclasses override this if some manipulation is needed
        return change_note

    def _process_line(self, line):
        try:
            line = str(line, "utf-8")
        except TypeError:
            pass
        return line.rstrip()

    def _is_excluded_line(self, line):
        if not line:
            return True

    def _is_start_line(self, line):
        if self.title:
            return line.upper() == "# {}".format(self.title.upper())

    def _is_end_line(self, line):
        # Also treat any new top level heading as end of section
        if line.startswith("# "):
            return True

    def _add_line(self, line):
        line = self._add_link(line)
        if self.h2_title:
            if self.h2_title not in self.h2:
                self.h2[self.h2_title] = []
            self.h2[self.h2_title].append(line)
            return
        self.content.append(line)

    def _add_link(self, line):
        return line

    def render(self, existing_content=""):
        if not self.content and not self.h2:
            return ""
        content = []
        content.append(self._render_header())
        if self.content:
            content.append(self._render_content())
        if self.h2:
            content.append(self._render_h2())
        return "\r\n".join(content)

    def _render_header(self):
        return "# {}\r\n".format(self.title)

    def _render_content(self):
        return "\r\n".join(self.content)

    def _render_h2(self):
        content = []
        for h2_title in self.h2.keys():
            content.append("\r\n## {}\r\n".format(h2_title))
            content.append("\r\n".join(self.h2[h2_title]))
        return "\r\n".join(content)


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


class IssuesParser(ChangeNotesLinesParser):
    def __init__(self, release_notes_generator, title, issue_regex=None):
        super(IssuesParser, self).__init__(release_notes_generator, title)
        self.issue_regex = issue_regex or self._get_default_regex()

    def _add_line(self, line):
        # find issue numbers per line
        issue_numbers = re.findall(self.issue_regex, line, flags=re.IGNORECASE)
        for issue_number in issue_numbers:
            self.content.append(int(issue_number))

    def _get_default_regex(self):
        return r"#(\d+)"

    def _render_content(self):
        issues = []
        for issue in sorted(self.content):
            issues.append("#{}".format(issue))
        return "\r\n".join(issues)


class GithubIssuesParser(IssuesParser):
    ISSUE_COMMENT = {
        "beta": "Included in beta release",
        "prod": "Included in production release",
    }

    def __new__(cls, release_notes_generator, title, issue_regex=None):
        if not release_notes_generator.has_issues:
            logging.getLogger(__file__).warn(
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


class InstallLinkParser(ChangeNotesLinesParser):
    def parse(self, change_note):
        # There's no need to parse lines, this parser gets its values from task options
        return False

    def render(self, existing_content=""):
        version_id = self.release_notes_generator.version_id
        trial_info = self.release_notes_generator.trial_info

        if (
            not version_id
            and not self.release_notes_generator.sandbox_date
            and not self.release_notes_generator.production_date
            and not trial_info
        ):
            return existing_content
        result = [self._render_header()]
        if (
            self.release_notes_generator.sandbox_date
            or self.release_notes_generator.production_date
        ):
            result.append("## Push Schedule")
            if self.release_notes_generator.sandbox_date:
                result.append(
                    f"Sandbox orgs: {self.release_notes_generator.sandbox_date}"
                )
            if self.release_notes_generator.production_date:
                result.append(
                    f"Production orgs: {self.release_notes_generator.production_date}",
                )
        if version_id:
            version_id = urllib.parse.quote_plus(version_id)
            if (
                self.release_notes_generator.sandbox_date
                or self.release_notes_generator.production_date
            ):
                result.append("")
            result += [
                "Sandbox & Scratch Orgs:",
                f"{SANDBOX_LOGIN_URL}/packaging/installPackage.apexp?p0={version_id}",
                "",
                "Production & Developer Edition Orgs:",
                f"{PROD_LOGIN_URL}/packaging/installPackage.apexp?p0={version_id}",
            ]

        if trial_info:
            if (
                version_id
                or self.release_notes_generator.sandbox_date
                or self.release_notes_generator.production_date
            ):
                result.append("")
            result += ["## Trialforce Template ID", f"{trial_info}"]
        return "\r\n".join(result)
