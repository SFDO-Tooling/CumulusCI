from setuptools import setup, find_packages

setup(
    name='cumulusci_ci',
    description='extension module for cumulusci to use ci related scripts/packages',
    packages=find_packages(exclude=['*.tests']),
    version='0.1',
)
