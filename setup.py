#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import re
from pkgutil import walk_packages

from setuptools import setup


def find_packages(path=["."], prefix=""):
    yield prefix
    prefix = prefix + "."
    for _, name, ispkg in walk_packages(path, prefix):
        if ispkg:
            yield name


with open(os.path.join("cumulusci", "version.txt"), "r") as version_file:
    version = version_file.read().strip()

with open("README.rst", "rb") as readme_file:
    readme = readme_file.read().decode("utf-8")

with open("HISTORY.rst", "rb") as history_file:
    history = history_file.read().decode("utf-8")

with open("requirements/prod.txt") as requirements_file:
    requirements = []
    for req in requirements_file.read().splitlines():
        # skip comments and hash lines
        if re.match(r"\s*#", req) or re.match(r"\s*--hash", req):
            continue
        else:
            req = req.split(" ")[0]
            # Work around normalized name of github3.py distribution
            req = req.replace("github3-py", "github3.py")
            requirements.append(req)

setup(
    name="cumulusci",
    version=version,
    description="Build and release tools for Salesforce developers",
    long_description=readme + "\n\n" + history,
    long_description_content_type="text/x-rst",
    author="Salesforce.org",
    author_email="sfdo-mrbelvedere@salesforce.com",
    url="https://github.com/SFDO-Tooling/CumulusCI",
    packages=list(find_packages(["cumulusci"], "cumulusci")),
    package_dir={"cumulusci": "cumulusci"},
    entry_points={
        "console_scripts": [
            "cci=cumulusci.cli.cci:main",
            "snowfakery=snowfakery.cli:main",
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="BSD license",
    zip_safe=False,
    keywords="cumulusci",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    test_suite="cumulusci.core.tests",
    python_requires=">=3.8",
)
