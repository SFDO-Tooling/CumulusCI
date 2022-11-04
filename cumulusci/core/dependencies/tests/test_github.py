from unittest import mock

import pytest
from github3.exceptions import NotFoundError

from cumulusci.core.config import BaseConfig
from cumulusci.core.dependencies.github import (
    get_package_data,
    get_remote_project_config,
    get_repo,
)
from cumulusci.core.exceptions import DependencyResolutionError


class DummyResponse(object):
    status_code = 404
    content = ""


def test_get_remote_project_config():
    content = b"""
project:
    package:
        namespace: foo"""

    repo = mock.Mock()
    repo.file_contents.return_value.decoded = content
    assert isinstance(get_remote_project_config(repo, "aaaaaaaa"), BaseConfig)


def test_get_repo():
    context = mock.Mock()

    assert get_repo("test", context) == context.get_repo_from_url.return_value


def test_get_repo__failure():
    context = mock.Mock()
    context.get_repo_from_url.return_value = None

    with pytest.raises(DependencyResolutionError):
        get_repo("test", context)


def test_get_repo__404():
    context = mock.Mock()
    context.get_repo_from_url.side_effect = NotFoundError(DummyResponse)

    with pytest.raises(DependencyResolutionError):
        get_repo("test", context)


def test_get_package_data():
    content = b"""
project:
    package:
        namespace: foo"""

    repo = mock.Mock()
    repo.file_contents.return_value.decoded = content

    assert get_package_data(get_remote_project_config(repo, "aaaaaaaa")) == (
        "Package",
        "foo",
    )
