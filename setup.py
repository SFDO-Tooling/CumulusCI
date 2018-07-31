#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from pkgutil import walk_packages

import cumulusci

def find_packages(path='.', prefix=""):
    yield prefix
    prefix = prefix + "."
    for _, name, ispkg in walk_packages(path, prefix):
        if ispkg:
            yield name

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'arrow==0.12.1',
    'click==6.7',
    'coloredlogs==9.3.1',
    'docutils==0.14',
    'future==0.16.0',
    'github3.py==0.9.6',
    'HiYaPyCo>=0.4.11',
    'lxml==4.2.1',
    'plaintable==0.1.1',
    'pycrypto==2.6.1',
    'PyGithub==1.39',
    'pytz==2018.4',
    'PyYAML==3.12',
    'raven==6.7.0',
    'requests[security]==2.18.4',
    'responses==0.9.0',
    'robotframework==3.0.4',
    'robotframework-seleniumlibrary==3.1.1',
    'rst2ansi==0.1.5',
    'salesforce-bulk==2.0.0',
    'sarge==0.1.4',
    'selenium==3.11.0',
    'simple-salesforce==0.74.2',
    'SQLAlchemy==1.2.7',
    'xmltodict==0.10.2',
]

test_requirements = [
    'coverage==4.1',
    'coveralls==1.2.0',
    'flake8==2.6.0',
    'mock==2.0.0',
    'nose==1.3.7',
    'nose-tap==1.9',
    'testfixtures==6.0.2',
    'tox==2.3.1',
]

setup(
    name='cumulusci',
    version='2.0.4',
    description="Build and release tools for Salesforce developers",
    long_description=readme + '\n\n' + history,
    author="Jason Lantz",
    author_email='jlantz@salesforce.com',
    url='https://github.com/SalesforceFoundation/CumulusCI',
    packages = list(find_packages(cumulusci.__path__, cumulusci.__name__)),
    package_dir={'cumulusci':
                 'cumulusci'},
    entry_points={
        'console_scripts': [
            'cci=cumulusci.cli.cci:main',
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="BSD license",
    zip_safe=False,
    keywords='cumulusci',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
    ],
    test_suite='cumulusci.core.tests',
    tests_require=test_requirements
)
