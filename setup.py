from setuptools import setup
from setuptools import find_packages

setup(
    name='cumulusci',
    version='2.0-prealpha',
    py_modules=['cumulusci'],
    packages=find_packages('core', 'tasks', 'salesforce_api'),
    package_dir={'': '.'},
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        cumulusci=cli.cumulusci:cli
        cumulusci2=newcli.cumulusci:cli
    ''',
)
