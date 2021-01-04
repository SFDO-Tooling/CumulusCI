#!/usr/bin/env python3

import sys

from github3 import login

from cumulusci import __version__ as version
from cumulusci.cli.runtime import CliRuntime

FORMULA_FILE = sys.argv[1]
TARGET_FILE = "cumulusci.rb"
GITHUB_ORG = "SFDO-Tooling"
GITHUB_REPO = "homebrew-sfdo"
BRANCH_NAME = "cci-" + version


def get_github_user():
    keychain_class = CliRuntime().get_keychain_class()
    keychain = keychain_class(
        CliRuntime().project_config, CliRuntime().get_keychain_key()
    )
    github_config = keychain.get_service("github")
    return github_config.username, github_config.password


def get_repo():
    username, password = get_github_user()
    gh = login(username=username, password=password)
    return gh.repository(GITHUB_ORG, GITHUB_REPO)


def create_branch(repo):
    head_sha = repo.ref("heads/{repo.default_branch}").object.sha
    branch_ref = f"refs/heads/{BRANCH_NAME}"
    print(f"Creating new branch from {head_sha[:8]} at {branch_ref}")
    repo.create_ref(branch_ref, head_sha)


def read_formula():
    with open(FORMULA_FILE, "r") as f:
        content = f.read().encode("utf-8")
    return content


def create_pull_request(repo):
    msg = f"Bump cumulusci to version {version}"
    new_commit = repo.file_contents(f"/{TARGET_FILE}").update(
        msg, read_formula(), branch=BRANCH_NAME
    )
    print(f"Updated {TARGET_FILE} to {new_commit['commit'].sha[:8]}")
    pull_request = repo.create_pull(msg, repo.default_branch, BRANCH_NAME)
    print(f"Created pull request at {pull_request.html_url}")


def main():
    repo = get_repo()
    create_branch(repo)
    create_pull_request(repo)


if __name__ == "__main__":
    main()
