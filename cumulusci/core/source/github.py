from typing import Type

from cumulusci.utils.yaml.cumulusci_yml import GitHubSourceModel, VCSSourceModel
from cumulusci.vcs.vcs_source import VCSSource


class GitHubSource(VCSSource):
    def __init__(self, project_config, spec: VCSSourceModel):
        super().__init__(project_config, spec)

    def __repr__(self):
        return f"<GitHubSource {str(self)}>"

    def __str__(self):
        s = f"GitHub: {self.repo.repo_owner}/{self.repo.repo_name}"
        if self.description:
            s += f" @ {self.description}"
        if self.commit != self.description:
            s += f" ({self.commit})"
        return s

    def __hash__(self):
        return hash((self.url, self.commit))

    @classmethod
    def source_model(self) -> Type[GitHubSourceModel]:
        return GitHubSourceModel

    def get_vcs_service(self):
        from cumulusci.vcs.github.service import get_github_service_for_url

        return get_github_service_for_url(self.project_config, self.url)

    def get_ref(self):
        return self.spec.ref

    def get_tag(self):
        return "tags/" + (self.spec.tag or "")

    def get_branch(self):
        return "heads/" + (self.spec.branch or "")

    def get_release_tag(self):
        return "tags/" + (self.spec.release or "")


class GitHubEnterpriseSource(GitHubSource):
    def get_vcs_service(self):
        """Get the GitHub Enterprise service for this source."""
        return super().get_vcs_service()
