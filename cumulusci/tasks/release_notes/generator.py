import github3.exceptions

from cumulusci.core.utils import import_global
from cumulusci.tasks.release_notes.exceptions import CumulusCIException
from cumulusci.tasks.release_notes.parser import ChangeNotesLinesParser
from cumulusci.tasks.release_notes.parser import GithubLinesParser
from cumulusci.tasks.release_notes.parser import IssuesParser
from cumulusci.tasks.release_notes.provider import StaticChangeNotesProvider
from cumulusci.tasks.release_notes.provider import DirectoryChangeNotesProvider
from cumulusci.tasks.release_notes.provider import GithubChangeNotesProvider


class BaseReleaseNotesGenerator(object):
    def __init__(self):
        self.change_notes = []
        self.empty_change_notes = []
        self.init_parsers()
        self.init_change_notes()

    def __call__(self):
        self._parse_change_notes()
        return self.render()

    def init_change_notes(self):
        self.change_notes = self._init_change_notes()

    def _init_change_notes(self):
        """ Subclasses should override this method to return an initialized
        subclass of BaseChangeNotesProvider """
        return []

    def init_parsers(self):
        """ Initializes the parser instances as the list self.parsers """
        self.parsers = []
        self._init_parsers()

    def _init_parsers(self):
        """ Subclasses should override this method to initialize their
        parsers """
        pass

    def _parse_change_notes(self):
        """ Parses all change_notes in self.change_notes() through all parsers
        in self.parsers """
        for change_note in self.change_notes():
            self._parse_change_note(change_note)

    def _parse_change_note(self, change_note):
        """ Parses an individual change note through all parsers in
        self.parsers. If no lines were added then appends the change
        note to the list of empty PRs"""
        line_added_by_parsers = False
        for parser in self.parsers:
            line_added = parser.parse(change_note)
            if parser.title == "Notes From Child PRs":
                parser._in_section = True
            if not line_added_by_parsers:
                line_added_by_parsers = line_added

        if not line_added_by_parsers:
            self.empty_change_notes.append(change_note)

    def render(self):
        """ Returns the rendered release notes from all parsers as a string """
        release_notes = []
        for parser in self.parsers:
            parser_content = parser.render()
            if parser_content is not None:
                release_notes.append(parser_content)
        return u"\r\n\r\n".join(release_notes)


class StaticReleaseNotesGenerator(BaseReleaseNotesGenerator):
    def __init__(self, change_notes):
        self._change_notes = change_notes
        super(StaticReleaseNotesGenerator, self).__init__()

    def _init_parsers(self):
        self.parsers.append(ChangeNotesLinesParser(self, "Critical Changes"))
        self.parsers.append(ChangeNotesLinesParser(self, "Changes"))
        self.parsers.append(IssuesParser(self, "Issues Closed"))

    def _init_change_notes(self):
        return StaticChangeNotesProvider(self, self._change_notes)


class DirectoryReleaseNotesGenerator(BaseReleaseNotesGenerator):
    def __init__(self, directory):
        self.directory = directory
        super(DirectoryReleaseNotesGenerator, self).__init__()

    def _init_parsers(self):
        self.parsers.append(ChangeNotesLinesParser(self, "Critical Changes"))
        self.parsers.append(ChangeNotesLinesParser(self, "Changes"))
        self.parsers.append(IssuesParser(self, "Issues Closed"))

    def _init_change_notes(self):
        return DirectoryChangeNotesProvider(self, self.directory)


class ParentPullRequestNotesGenerator(BaseReleaseNotesGenerator):
    """Aggregates notes from PRs with parent_pr_num as their base."""

    def __init__(self, github, repo, project_config, branch_name, parent_branch_name):
        self.REPO_OWNER = project_config.repo_owner
        self.BUILD_NOTES_LABEL = "Build Change Notes"
        self.UNAGGREGATED_SECTION_HEADER = "\r\n\r\n# Unaggregated Pull Requests"

        self.repo = repo
        self.link_pr = True  # create links to pr on parsed change notes
        self.github = github
        self.has_issues = True
        self.do_publish = True
        self.target_branch = branch_name
        self.parent_branch = parent_branch_name
        self.feature_branch_prefix = project_config.project__git__prefix_feature
        self.parser_config = (
            project_config.project__git__release_notes__parsers.values()
        )
        super(ParentPullRequestNotesGenerator, self).__init__()

    def _init_parsers(self):
        for cfg in self.parser_config:
            parser_class = import_global(cfg["class_path"])
            self.parsers.append(parser_class(self, cfg["title"]))

        # New parser to collect notes above tracked sections
        self.parsers.append(GithubLinesParser(self, "Notes From Child PRs"))
        self.parsers[-1]._in_section = True

    def execute(self):
        """Determines how to acquire the 'parent' pull request given the available parameters"""
        if self.parent_branch:
            parent_pull_request = self._get_pr_by_branch_name(self.parent_branch)
        elif self._branch_is_child_of_feature(self.target_branch):
            pull_requests = self._get_parent_pull_request(self.parent_branch)
            if len(pull_requests) == 0:
                parent_pull_request = self._create_parent_pr()
            elif len(pull_requests) == 1:
                parent_pull_request = pull_requests[0]
            else:
                raise CumulusCIException(
                    "Expected 0 or 1 pull request, but received {}".format(
                        len(pull_requests)
                    )
                )
        else:
            # if we don't have parent branch specified AND target_branch is
            # not a child of a feature branch, then we're done
            return
        self._process_parent_pull_request(parent_pull_request)

    def _process_parent_pull_request(self, parent_pull_request):
        """Alters the body of the parent pull request based on the presence of the 'Build Change Notes'
        label. 
        
        If the label is present, we aggregate all change note information
        from child pull requests and recreates the parent_pull_reqeust body. 

        In the absence of the label, we append links to any new child PRs to the
        'Unaggregated Pull Requests' section of the parent_pull_request"""
        if self._is_label_on_pr(parent_pull_request.number, self.BUILD_NOTES_LABEL):
            self.change_notes = self._get_child_pull_requests(self.parent_branch)
            if not self.change_notes:
                raise CumulusCIException(
                    "No child PRs found for Pull Request #{}".format(
                        parent_pull_request.number
                    )
                )
            for change_note in self.change_notes:
                self._parse_change_note(change_note)

            body = []
            for parser in self.parsers:
                parser_content = parser.render()
                if parser_content:
                    body.append(parser_content)

            if self.empty_change_notes:
                body.extend(render_empty_pr_section(self.empty_change_notes))
            new_body = "\r\n".join(body)
            if not parent_pull_request.update(body=new_body):
                raise CumulusCIException(
                    "Update of pull request {} failed.".format(
                        parent_pull_request.number
                    )
                )
        elif self.target_branch:
            self._update_unaggregated_pr_list(parent_pull_request)

    def _branch_is_child_of_feature(self, target_branch):
        """Returns true if the branch with the given name is the child of a feature branch. False otherwise."""
        pr = self._get_pr_by_branch_name(target_branch)
        self.parent_branch = pr.base.ref
        return self.parent_branch.startswith(self.feature_branch_prefix)

    def _get_parent_pull_request(self, parent_branch):
        """Returns a list of all pull requests with head=parent_branch
        and base=master"""
        return list(
            self.repo.pull_requests(
                head=self.REPO_OWNER + ":" + parent_branch, base="master"
            )
        )

    def _get_child_pull_requests(self, parent_branch):
        """Get all pull requests with parent_branch as base"""
        return list(self.repo.pull_requests(base=parent_branch))

    def _create_parent_pr(self):
        """Creates a pull request for self.parent_branch,
        and adds the BUILD_NOTES_LABEL labe to it."""
        try:
            parent_pr = self.repo.create_pull(
                "Auto Generated Pull Request", "master", self.parent_branch
            )
        except Exception as e:
            raise CumulusCIException("Error creating pull request:\n{}".format(e))
        self._add_label_to_pr(parent_pr.number, [self.BUILD_NOTES_LABEL])
        return parent_pr

    def _add_label_to_pr(self, pr_num, labels):
        """Adds a label to a pull request via the issue object"""
        issue = self.repo.issue(pr_num)
        issue.add_label(labels)

    def _is_label_on_pr(self, pr_num, label_name):
        """Returns True if the given label is on the pull request with the given
        pull request number. False otherwise."""
        return any(
            label_name in pr_label.name for pr_label in self.repo.issue(pr_num).labels()
        )

    def _update_unaggregated_pr_list(self, parent_pr):
        body = parent_pr.body
        if self.UNAGGREGATED_SECTION_HEADER not in body:
            body += self.UNAGGREGATED_SECTION_HEADER

        pull_request = self._get_pr_by_branch_name(self.target_branch)
        body += "\r\n* " + markdown_link_to_pr(pull_request)
        parent_pr.update(body=body)

    def _get_pr_by_branch_name(self, branch_name):
        pull_requests = list(
            self.repo.pull_requests(head=self.REPO_OWNER + ":" + branch_name)
        )
        if len(pull_requests) == 1:
            return pull_requests[0]
        else:
            raise CumulusCIException(
                "Expected one pull request but received {}".format(len(pull_requests))
            )


class GithubReleaseNotesGenerator(BaseReleaseNotesGenerator):
    def __init__(
        self,
        github,
        github_info,
        parser_config,
        current_tag,
        last_tag=None,
        link_pr=False,
        publish=False,
        has_issues=True,
        include_empty=False,
    ):
        self.github = github
        self.github_info = github_info
        self.parser_config = parser_config
        self.current_tag = current_tag
        self.last_tag = last_tag
        self.link_pr = link_pr
        self.do_publish = publish
        self.has_issues = has_issues
        self.include_empty_pull_requests = include_empty
        self.lines_parser_class = None
        self.issues_parser_class = None
        super(GithubReleaseNotesGenerator, self).__init__()

    def __call__(self):
        release = self._get_release()
        content = super(GithubReleaseNotesGenerator, self).__call__()
        content = self._update_release_content(release, content)
        if self.do_publish:
            release.edit(body=content)
        return content

    def _init_parsers(self):
        for cfg in self.parser_config:
            parser_class = import_global(cfg["class_path"])
            self.parsers.append(parser_class(self, cfg["title"]))

    def _init_change_notes(self):
        return GithubChangeNotesProvider(self, self.current_tag, self.last_tag)

    def _get_release(self):
        repo = self.get_repo()
        try:
            return repo.release_from_tag(self.current_tag)
        except github3.exceptions.NotFoundError:
            raise CumulusCIException(
                "Release not found for tag: {}".format(self.current_tag)
            )

    def _update_release_content(self, release, content):
        """Merge existing and new release content."""
        new_body = []
        if release.body:
            current_parser = None
            is_start_line = False
            for parser in self.parsers:
                parser.replaced = False

            # update existing sections
            for line in release.body.splitlines():

                if current_parser:
                    if current_parser._is_end_line(current_parser._process_line(line)):
                        parser_content = current_parser.render()
                        if parser_content:
                            # replace existing section with new content
                            new_body.append(parser_content + "\r\n")
                        current_parser = None

                for parser in self.parsers:
                    if (
                        parser._render_header().strip()
                        == parser._process_line(line).strip()
                    ):
                        parser.replaced = True
                        current_parser = parser
                        is_start_line = True
                        break
                    else:
                        is_start_line = False

                if is_start_line:
                    continue
                if current_parser:
                    continue
                else:
                    # preserve existing sections
                    new_body.append(line.strip())

            # catch section without end line
            if current_parser:
                new_body.append(current_parser.render())

            # add new sections at bottom
            for parser in self.parsers:
                parser_content = parser.render()
                if parser_content and not parser.replaced:
                    new_body.append(parser_content + "\r\n")

        else:  # no release.body
            new_body.append(content)

        # add empty PR section
        if self.include_empty_pull_requests:
            new_body.extend(render_empty_pr_section(self.empty_change_notes))
        content = u"\r\n".join(new_body)
        return content

    def get_repo(self):
        return self.github.repository(
            self.github_info["github_owner"], self.github_info["github_repo"]
        )


def render_empty_pr_section(empty_change_notes):
    section_lines = []
    if empty_change_notes:
        section_lines.append("\n# Pull requests with no release notes")
        for change_note in empty_change_notes:
            section_lines.append("\n* {}".format(markdown_link_to_pr(change_note)))
    return section_lines


def markdown_link_to_pr(change_note):
    return "{} [[PR{}]({})]".format(
        change_note.title, change_note.number, change_note.html_url
    )
