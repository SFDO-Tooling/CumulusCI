from io import StringIO
from unittest import mock

import pytest

from cumulusci.core.config import BaseConfig
from cumulusci.core.dependencies.github import get_github_repo
from cumulusci.core.dependencies.resolvers import get_package_data
from cumulusci.core.exceptions import DependencyResolutionError, GithubApiNotFoundError
from cumulusci.vcs.bootstrap import get_remote_project_config
from cumulusci.vcs.tests.dummy_service import DummyRepo


class DummyResponse(object):
    status_code = 404
    content = ""


def test_get_remote_project_config():
    content = b"""
project:
    package:
        namespace: foo"""

    mock_repo = DummyRepo()
    repo = mock.Mock()
    repo.file_contents.return_value = StringIO(content.decode("utf-8"))
    mock_repo.repo = repo
    assert isinstance(get_remote_project_config(mock_repo, "aaaaaaaa"), BaseConfig)


@mock.patch("cumulusci.vcs.github.service.GitHubService.get_service_for_url")
def test_get_github_repo_basic(github_service_mock):
    context = mock.Mock(name="project_config")
    repo = DummyRepo()
    vcs_service = mock.Mock(name="vcs_service")
    vcs_service.get_repository.return_value = repo
    github_service_mock.return_value = vcs_service

    result = get_github_repo(context, "https://github.com/test/repo")
    assert result == repo
    vcs_service.get_repository.assert_called_once_with(
        options={"repository_url": "https://github.com/test/repo"}
    )


@mock.patch("cumulusci.vcs.github.service.GitHubService.get_service_for_url")
@mock.patch("cumulusci.vcs.github.service.GitHubEnterpriseService.get_service_for_url")
def test_get_repo__failure(github_service_mock, github_enterprise_service_mock):
    context = mock.Mock(name="project_config")
    github_service_mock.return_value = None
    github_enterprise_service_mock.return_value = None

    with pytest.raises(DependencyResolutionError):
        get_github_repo(context, "https://abc.com/test/repo")


@mock.patch("cumulusci.vcs.github.service.GitHubService.get_service_for_url")
def test_get_repo__404(github_service_mock):
    context = mock.Mock(name="project_config")
    vcs_service = mock.Mock(name="vcs_service")
    vcs_service.get_repository.side_effect = GithubApiNotFoundError(DummyResponse)
    github_service_mock.return_value = vcs_service

    with pytest.raises(DependencyResolutionError):
        get_github_repo(context, "test")


def test_get_package_data():
    content = b"""
project:
    package:
        namespace: foo"""

    mock_repo = DummyRepo()
    repo = mock.Mock()
    repo.file_contents.return_value = StringIO(content.decode("utf-8"))
    mock_repo.repo = repo

    assert get_package_data(get_remote_project_config(mock_repo, "aaaaaaaa")) == (
        "Package",
        "foo",
    )
