===============
Usage in Python
===============

While most users of CumulusCI use the included command-line interface, ``cci``, it is also a library that can be invoked from any Python application. We take advantage of this to provide apps like MetaCI and MetaDeploy that run CumulusCI automation inside Django apps on Heroku. 

The Python API is primarily for internal users, but rough documentation is provided for experimentation and understanding of the code.


Runtime
-------

The main entry point to CumulusCI is through a Runtime object. ``cumulusci.core.runtime.BaseRuntime`` is a concrete class and sufficient to create a simple CCI, and ``cumulusci.cci.config.CliRuntime`` contains examples of a runtime configured to dynamically provide the Keychain implementation, as well as handle errors differently.

To use a Runtime, just contruct it::

    runtime = BaseRuntime()
    runtime.project_config.get_task('Blah')()