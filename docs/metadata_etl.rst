.. _metadata-etl:

============
Metadata ETL
============

Introduction to Metadata ETL
----------------------------

"ETL" refers to "extract, transform, and load" operations, usually applied
to data. CumulusCI offers a suite of functionality we call *Metadata ETL*.
Metadata ETL makes it easy to define automation that executes targeted
transformations of metadata that already exists in an org.

Metadata ETL is particularly useful for building automation in projects
that extend other managed packages or that perform complex setup operations
during installations, such as through MetaDeploy. By using Metadata ETL
tasks, projects can often avoid storing and deploying unpackaged metadata
by instead extracting metadata from the target org, making changes, and
then re-deploying. This mode of configuration is lower-risk and lower-
maintenance than storing extensive unpackaged metadata, which may
become out-of-sync, incur accidental feature dependencies, or entail more destructive deployment operations.

A primary example use case for Metadata ETL is deployment of Standard Value Sets.
Standard Value Sets, which define the picklist values available on standard fields
like ``Opportunity.StageName``, are not packageable, and as such must be part of an
application's unpackaged metadata. They're critical to many applications: A Business
Process, for example, will fail to deploy if the Stage values it includes are not available.
And lastly, they come with a serious danger for deployment into subscriber orgs:
deploying Standard Value Sets is an overwrite operation, so all existing values in the
target org that aren't part of the deployment are deactivated. This means that it's
neither safe nor maintainable to store static Standard Value Set metadata in a project
and deploy it.

These three facets - non-packageability, application requirements, and deployment safety -
all support a Metadata ETL approach. Rather than attempting to deploy static metadata
stored in the repository, the product's automation should *extract* the Standard Value Set 
metadata from the org, *transform* it to include the desired values (as well as all existing
customization), and *load* the transformed metadata back into the org. CumulusCI now ships
with a task, ``add_standard_value_set_entries``, that makes it easy to do just this:

  .. code-block:: yaml

    add_standard_value_set_entries:
        options:
            entries:
                - fullName: "New_Value"
                  label: "New Value"
                  closed: False
            api_names:
                - CaseStatus

This task would retrieve the existing ``Case.Status`` picklist value set from the org,
add the ``New_Value`` entry to it, and redeploy the modified metadata - ensuring that
the application's needs are met with a safe, minimal intervention in the target org.

Standard Metadata ETL Tasks
---------------------------

CumulusCI includes several Metadata ETL tasks in its standard library.
For information about all of the available tasks, see TODO: link Metadata Transformations task group.

Most Metadata ETL tasks accept the option ``api_names``, which specifies the developer names of the specific metadata components which should be included in the operation.
In most cases, more than one entity may be transformed in a single operation.
Each task performs a single Metadata API retrieve and a single atomic deployment.
Please note, however, that the extract-transform-load operation as a whole is *not* atomic; it is not safe to run Metadata ETL tasks in parallel or to mutate metadata by other means during the run of a Metadata ETL task.

Consult the Task Reference or use the ``cci task info`` command for more information on the usage of each task.

The Metadata ETL framework makes it easy to add more tasks.
For information about implementing Metadata ETL tasks, see TODO: link to section in Python customization.

Namespace Injection
-------------------

All out-of-the-box Metadata ETL tasks accept a Boolean ``managed`` option. If ``True``, CumulusCI
will replace the token ``%%%NAMESPACE%%%`` in API names and in values used for transforming metadata
with the project's namespace; if ``False``, the token will simply be removed. See :ref:`Namespace Injection` for more information.
