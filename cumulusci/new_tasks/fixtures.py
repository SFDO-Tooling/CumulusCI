import logging

from github3.repos import Repository
from simple_salesforce import Salesforce

from cumulusci.core.config import BaseProjectConfig, OrgConfig

__all__ = ["sf", "repo", "logger", "org", "project"]


def sf(o: OrgConfig, _p: BaseProjectConfig) -> Salesforce:
    return o.salesforce_client


def repo(_o: OrgConfig, p: BaseProjectConfig) -> Repository:
    return project.get_repo()


def logger(_o: OrgConfig, _p: BaseProjectConfig) -> logging.Logger:
    return logging.getLogger(__name__)


def org(o: OrgConfig, _p: BaseProjectConfig) -> OrgConfig:
    return o


def project(_o: OrgConfig, p: BaseProjectConfig) -> BaseProjectConfig:
    return p
