from setuptools import setup

setup(
    name='cumulusci',
    version='0.1',
    py_modules=['cumulusci'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        cumulusci=cumulusci:cli
    ''',
)
