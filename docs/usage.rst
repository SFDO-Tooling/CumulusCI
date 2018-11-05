===============
Usage in Python
===============

While most users of CumulusCI use the included command-line interface, ``cci``, it is also a library that can be invoked from any Python application. We take advantage of this to provide apps like MetaCI and MetaDeploy that run CumulusCI automation inside Django apps on Heroku. 

The Python API is primarily for internal users, but rough documentation is provided for experimentation and understanding of the code.


Runtime
-------

The main entry point to CumulusCI is through a Runtime object. ``cumulusci.core.runtime.BaseCumulusCI`` is a concrete class and sufficient to create a simple CCI, and ``cumulusci.cci.config.CliRuntime`` contains examples of a runtime configured to dynamically provide the Keychain implementation, as well as handle errors differently.

To use a Runtime, just contruct it::

    runtime = BaseCumulusCI()
    runtime.project_config.get_task('Blah')()

If the current working directory isn't inside a git repository (as determined by there being a .git folder in or above the current directory), you'll want to pass in repo information instead.::

    runtime = BaseCumulusCI(repo_info={'root': '/Absolute/Path/To/Workspace', 'branch': 'feature/mybranch', 'name': 'Workspace', 'owner': 'MyThing', 'url':'private-url', 'commit': 'shaish'})

Okay, you don't need to provide all of those. The only one that's necessary is the 'root' key, unless you're using a task that uses the other information. So, a frequent invocation is simply::

    runtime = BaseCumulusCI(repo_info={'root':'/Users/cdcarter/Projects/CumulusCI-Test'})

.