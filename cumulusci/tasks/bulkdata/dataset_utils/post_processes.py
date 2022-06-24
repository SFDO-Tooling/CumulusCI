from typing import NamedTuple


def add_after_statements(mappings):
    """Automatically add CCI after: statements to the lookups
    in a mapping file"""
    indexed_by_sobject = _index_by_sobject(mappings)

    for idx, (mapping_name, mapping) in enumerate(mappings.items()):
        for lookup in mapping.get("lookups", {}).values():
            target_table = lookup["table"]
            # PersonContacts are not real
            if target_table == "PersonContact":
                continue
            target_mapping_index = indexed_by_sobject[target_table]
            if target_mapping_index.first_instance >= idx:
                if not lookup.get("after"):
                    lookup["after"] = target_mapping_index.last_step_name


class MappingIndex(NamedTuple):  # info needed by the algorithm above
    first_instance: int  # where was the first time this sobj was referenced?
    last_step_name: str  # where was the last (so far)?


def _index_by_sobject(mappings):
    indexed_by_sobject = {}
    for idx, (mapping_name, mapping) in enumerate(mappings.items()):
        # make an index of the order of objects
        sobject = mapping["sf_object"]
        existing_index = indexed_by_sobject.get(sobject)

        if existing_index:
            new_mi = MappingIndex(existing_index.first_instance, mapping_name)
        else:
            new_mi = MappingIndex(idx, mapping_name)
        indexed_by_sobject[sobject] = new_mi

    return indexed_by_sobject
