from cumulusci.core.config import OrgConfig, BaseProjectConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.runtime import BaseCumulusCI
import click
import yaml
import os
from importlib.resources import files
from .runtime import pass_runtime

@click.group(name="check", help="Run health checks on the target Salesforce org.")
def check():
    """Command group for running health checks on the Salesforce org."""
    pass
                
@check.command(name="sobject_checks", help="Check SObjects")
@click.option('--org', help="")
@pass_runtime(require_project=True, require_keychain=True)
def sobject_checks(runtime, org):
    org, org_config = runtime.get_org(org)
    click.echo(f"Running SObject health checks on org: {org_config.name}")
    
    sobjects = runtime.project_config.check["sobjects"] or {}

    sobject_map = {
        'PermissionSetAssignment': {
            'fields': ['PermissionSet.Name'],
            'where': f"AssigneeId = '{org_config.user_id}'"
        },
        'PermissionSet': {
            'fields': ['Name'],
        }
    }
    
    failures = []
    for sobject in sobjects:
        object_name = sobject['object']
        click.echo(f"sobject {sobject}")
        fields = sobject_map[object_name]['fields']
        values = sobject['values']
        joined_fields = ', '.join(fields)
        where_clause = sobject_map[object_name].get('where')
 
        query = f"SELECT {joined_fields} FROM {object_name}"
        query = query + f' WHERE {where_clause}' if where_clause else query
        query_result = org_config.salesforce_client.query(query)
        if not query_result['records']:
            click.echo(f"No records found for {object_name} with fields {fields}.")
            failures.append(object_name)
            continue
        else:
            click.echo(f"Records found for {object_name} with fields {fields}.")

        values_to_test = []
        for field in fields:
            values_to_test.append([record[field] for record in query_result['records']])
        all_present = all(test_value in values_to_test for test_value in values)
        if not all_present:
            failures.append(object_name)


    

