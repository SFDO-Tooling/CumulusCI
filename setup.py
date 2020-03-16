#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
from setuptools import setup
from pkgutil import walk_packages


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

with open("requirements.txt") as requirements_file:
    requirements = [
        req.split("#")[0].strip() for req in requirements_file.read().splitlines()
    ]

with open("requirements_dev.txt") as dev_requirements_file:
    test_requirements = [
        req
        for req in dev_requirements_file.read().splitlines()
        if not req.startswith("-")
    ]


setup(
    name="cumulusci",
    version=version,
    description="Build and release tools for Salesforce developers",
    long_description=readme + u"\n\n" + history,
    long_description_content_type="text/x-rst",
    author="Salesforce.org",
    author_email="jlantz@salesforce.com",
    url="https://github.com/SFDO-Tooling/CumulusCI",
    packages=list(find_packages(["cumulusci"], "cumulusci")),
    package_dir={"cumulusci": "cumulusci"},
    entry_points={"console_scripts": ["cci=cumulusci.cli.cci:main"]},
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    test_suite="cumulusci.core.tests",
    tests_require=test_requirements,
    python_requires=">=3.6",
)
