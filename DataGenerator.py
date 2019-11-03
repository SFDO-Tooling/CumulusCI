from collections import defaultdict
from dataclasses import dataclass
from functools import partial

import jinja2

from cumulusci.core.template_utils import format_str

from template_funcs import template_funcs


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


class Globals:
    def __init__(self, variables):
        self.named_objects = {}
        self.id_manager = IdManager()
        self.variables = variables

    def register_object(self, nickname, obj):
        self.named_objects[nickname] = obj

    def find_object_by_name(self, nickname):
        return self.named_objects[nickname]

    def get_object_id_by_name(self, nickname):
        return self.named_objects[nickname].fields["id"]


class Context:
    current_id = None
    obj = None

    def __init__(self, parent, sobject_name, storage_engine=None, variables=None):
        self.parent = parent
        self.sobject_name = sobject_name
        self.counter_generator = CounterGenerator(
            parent.counter_generator if parent else None
        )
        self.globals = parent.globals if parent else Globals(variables)
        self.storage_engine = storage_engine or self.parent.storage_engine

    def incr(self):
        self.counter_generator.incr(self.sobject_name)

    def get_id(self):
        self.current_id = self.globals.id_manager.get_id(self.sobject_name)
        return self.current_id

    def register_object(self, name, obj):
        self.globals.register_object(name, obj)

    def output_child_row(self, sobj):
        return self.storage_engine.output(sobj, self)[0]

    def field_vars(self):
        funcs = {name: partial(func, self) for name, func in template_funcs.items()}
        return {
            "id": self.current_id,
            "number": self.counter_generator.get_value(self.sobject_name),
            "counter": self.counter_generator.get_value,
            "reference": self.globals.get_object_id_by_name,
            **funcs,
        }


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
    nickname: str = None

    def generate_rows(self, storage, parent_context):
        context = Context(parent_context, self.sftype)
        assert isinstance(self.count, int), self.count
        return [self._generate_row(storage, context) for i in range(self.count)]

    def _generate_row(self, storage, context):
        context.incr()
        row = {"id": context.get_id()}
        sobj = SObject(self.sftype, row)
        if self.nickname:
            context.register_object(self.nickname, sobj)

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
