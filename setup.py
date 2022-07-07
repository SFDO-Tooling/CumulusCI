#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pkgutil import walk_packages

from setuptools import setup


def find_packages(path=["."], prefix=""):
    yield prefix
    prefix = prefix + "."
    for _, name, ispkg in walk_packages(path, prefix):
        if ispkg:
            yield name


setup(
    packages=list(find_packages(["cumulusci"], "cumulusci")),
    test_suite="cumulusci.core.tests",
)
