from collections import defaultdict
from copy import copy
from dataclasses import dataclass
from datetime import datetime

import jinja2

from cumulusci.core.template_utils import format_str


class IdManager:
    def __init__(self):
        self.last_used_ids = defaultdict(lambda: 0)

    def get_id(self, sobject_name):
        self.last_used_ids[sobject_name] += 1
        return self.last_used_ids[sobject_name]


class CounterGenerator:
    def __init__(self, parent):
        self.counters = defaultdict(lambda: 0)
        self.root_counter = parent.root_counter if parent else self

    def set_value(self, name, value):
        if name.startswith("/"):
            self.root_counter.set_value(name[1:], value)
        else:
            self.counters[name] = value

    def get_value(self, name):
        if name.startswith("/") and self.root_counter != self:
            value = self.root_counter.get_value(name[1:])
        else:
            value = self.counters[name]

        return value

    def incr(self, sobject_name):
        self.counters[sobject_name] += 1
        self.root_counter.counters[sobject_name] += 1


class Context:
    current_id = None

    def __init__(self, parent, sobject_name, storage_engine=None):
        self.parent = parent
        self.sobject_name = sobject_name
        self.counter_generator = CounterGenerator(
            parent.counter_generator if parent else None
        )
        self.id_manager = parent.id_manager if parent else IdManager()
        self.references = {}
        self.storage_engine = storage_engine or self.parent.storage_engine

    def register_row(self, refname, row):
        self.references[refname] = row

    def incr(self):
        self.counter_generator.incr(self.sobject_name)

    def field_vars(self):
        return {
            "id": self.current_id,
            "number": self.counter_generator.get_value(self.sobject_name),
            "Counter": self.counter_generator.get_value,
            "AncestorField": self.ancestor_field,
            "OtherField": self.other_field,
            "Ancestor": self.ancestor_id,
            "now": self.now,
        }

    def parent_field(self, name):
        return self.parent.obj.fields[name]

    def other_field(self, name):
        return self.objs.fields[name]

    def ancestor_id(self, sobject_name):
        return self.ancestor_field(sobject_name, "id")

    def ancestor_field(self, sobject_name, field_name):
        current_context = self
        while current_context:
            if current_context.obj.sftype == sobject_name:
                return current_context.obj.fields[field_name]
            else:
                current_context = current_context.parent

    def now(self):
        return datetime.now()

    def get_id(self):
        self.current_id = self.id_manager.get_id(self.sobject_name)
        return self.current_id

    def output_child_row(self, sobj):
        return self.storage_engine.output(sobj, self)[0]


class StorageEngine:
    def __init__(self):
        self.cg = CounterGenerator(None)

    def output_batches(self, factory, number):
        context = Context(None, None, self)
        duplicated_factory = copy(factory)
        duplicated_factory.count = number * factory.count
        return self.output(duplicated_factory, context)

    def output(self, factory, context):
        return factory.generate_rows(self, context)

    def write_row(self, tablename, row):
        assert 0, "Not implemented"


class DebugOutputEngine(StorageEngine):
    def write_row(self, tablename, row):
        print(tablename, row)


@dataclass
class SObject:
    sftype: str
    fields: list


@dataclass
class SObjectFactory:
    sftype: str
    count: int = 1
    fields: list = ()
    friends: list = ()

    def generate_rows(self, storage, parent_context):
        context = Context(parent_context, self.sftype)
        assert isinstance(self.count, int), self.count
        return [self._generate_row(storage, context) for i in range(self.count)]

    def _generate_row(self, storage, context):
        context.incr()
        row = {"id": context.get_id()}
        sobj = SObject(self.sftype, row)
        context.obj = sobj

        for field in self.fields:
            row[field.name] = field.generate_value(context)

        storage.write_row(self.sftype, row)
        for i, childobj in enumerate(self.friends):
            childobj.generate_rows(storage, context)
        return row


class FieldDefinition:
    def render(self, context):
        pass


class FieldValue:
    pass


@dataclass
class SimpleValue(FieldDefinition):
    definition: str

    def render(self, context):
        try:
            return format_str(self.definition, **context.field_vars())
        except jinja2.exceptions.TemplateSyntaxError as e:
            raise Exception(f"Error in parsing {self.definition}: {e}")


@dataclass
class ChildRecordValue(FieldDefinition):
    sobj: object

    def render(self, context):
        child_row = context.output_child_row(self.sobj)

        return child_row["id"]


@dataclass
class FieldFactory:
    name: str
    definition: object

    def generate_value(self, context):
        return self.definition.render(context)
