import itertools
import typing as T

from snowfakery.salesforce import find_record_type_column

from cumulusci.tasks.bulkdata.mapping_parser import MappingStep
from cumulusci.tasks.bulkdata.step import DataOperationType
from cumulusci.utils.yaml.model_parser import CCIModel

"""A mapping transform is a function with the signature:

def func(mapping_steps: T.List[MappingStep], depmap: "DependencyMap") -> T.List[MappingStep]:

It should be idempotent and a pure function (don't mutate arguments).

Ideally the output should be as similar to the input as possible (i.e.
change what you need to change and leave the rest as it was). In particular,
the order of the input steps should be preserved unless reordering them
is the specific task of the transform.
"""

from cumulusci.tasks.bulkdata.generate_mapping_utils.dependency_map import DependencyMap


def sort_steps(
    mapping_steps: T.List[MappingStep], depmap: DependencyMap
) -> T.List[MappingStep]:
    """Sort mapping declaration steps in dependency order"""
    table_order = depmap.get_dependency_order()

    return sorted(mapping_steps, key=lambda step: table_order.index(step.sf_object))


class _MappingStepSignature(CCIModel):
    index: int
    sf_object: T.Optional[str]
    filters: T.Optional[T.Tuple[str]] = ()
    soql_filter: T.Optional[str] = None  # soql_filter property
    action: DataOperationType
    update_key: T.Union[str, T.Tuple[str, ...]] = ()  # only for upserts


def merge_matching_steps(
    steps: T.Iterable[MappingStep], depmap: DependencyMap
) -> T.List[MappingStep]:
    """Merge mapping declaration steps with similar properties"""
    table_order = {obj.sf_object: idx for idx, obj in enumerate(steps)}
    grouped_steps = itertools.groupby(
        steps,
        lambda step: _MappingStepSignature(
            index=table_order[step.sf_object],
            sf_object=step.sf_object,
            filters=tuple(step.filters) or None,
            soql_filter=step.soql_filter,
            action=step.action,
            update_key=step.update_key,
        ),
    )

    new_steps = [_merge_steps(steps) for _group, steps in grouped_steps]
    return new_steps


def _merge_steps(steps: T.Iterable[MappingStep]) -> MappingStep:
    """Merge a groupp of matching steps together"""
    steps = tuple(steps)
    new_props = steps[0].dict()
    new_props["fields"] = {}
    new_props["lookups"] = {}
    for step in steps:
        new_props["fields"].update(step.fields)
        new_props["lookups"].update(step.lookups)
    return MappingStep(**new_props)


def rename_record_type_fields(
    mapping_steps: T.List[MappingStep], depmap: DependencyMap
) -> T.List[MappingStep]:
    """Rename fields like recordtype, recordtypeid, recordtype_id to RecordTypeId"""

    def doit(mapping_step: MappingStep):
        table_name = mapping_step.sf_object
        record_type_col = find_record_type_column(table_name, mapping_step.fields)
        if record_type_col:
            fields = mapping_step.fields.copy()
            fields["RecordTypeId"] = fields.pop(record_type_col)
            return MappingStep(**{**mapping_step.dict(), "fields": fields})
        else:
            return mapping_step

    return list(map(doit, mapping_steps))


def recategorize_lookups(
    mapping_steps: T.List[MappingStep], depmap: DependencyMap
) -> T.List[MappingStep]:
    """Categorize fields which are actually lookups

    Put them in mapping_step.lookup and remove them from mapping_step.fields"""

    def doit(mapping_step: MappingStep):
        table_name = mapping_step.sf_object
        lookups = mapping_step.lookups.copy() or {}
        lookups.update(
            {
                fieldname: {
                    "table": depmap.target_table_for(table_name, fieldname),
                    "key_field": fieldname,
                }
                for fieldname in mapping_step.fields
                if depmap.target_table_for(table_name, fieldname)
            }
        )

        if lookups:
            fields = [
                field for field in mapping_step.fields if field not in lookups.keys()
            ]
            return MappingStep(
                **{**mapping_step.dict(), "lookups": lookups, "fields": fields}
            )
        else:
            return mapping_step

    return list(map(doit, mapping_steps))


# SnowfakeryPersonAccounts: This will be turned on when Snowfakery is
# integrated with this code.
#
# def change_person_contact_sf_object(
#     mapping_steps: T.List[MappingStep], depmap: DependencyMap
# ) -> T.List[MappingStep]:
#     def doit(mapping_step: MappingStep):

#         if mapping_step.table_name == "PersonContact":
#             mapping_step.sf_object = "Contact"

#     return list(map(doit, mapping_steps))
