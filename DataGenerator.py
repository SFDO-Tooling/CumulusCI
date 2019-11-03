from collections import defaultdict
from dataclasses import dataclass
from functools import partial

import jinja2

from cumulusci.core.template_utils import faker_template_library

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

    def evaluate_jinja(self, definition):
        # todo cache templates at compile time and reuse evaluator
        if isinstance(definition, str) and "<<" in definition:
            environment = JinjaTemplateEvaluator()
            evaluator = environment.get_evaluator(definition)

            return environment.evaluate(
                evaluator, variables=self.field_vars(), funcs=self.field_funcs()
            )
        else:
            return definition

    # def evaluate_simple_eval(self, definition):
    #     if definition[0] == "=":
    #         definition = definition[1:]
    #         # todo: should reuse parsed code objcts
    #         return simpleeval.simple_eval(
    #             definition, names=self.globals.variables, functions=self.field_vars
    #         )
    #     else:
    #         return definition

    evaluate = evaluate_jinja

    def field_vars(self):
        return {"id": self.current_id, **self.globals.variables}

    def field_funcs(self):
        funcs = {name: partial(func, self) for name, func in template_funcs.items()}
        return {
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
    count_expr: str = None
    fields: list = ()
    friends: list = ()
    nickname: str = None

    def generate_rows(self, storage, parent_context):
        context = Context(parent_context, self.sftype)
        if self.count_expr and self.count is None:
            self.count = int(float(self.count_expr.render(context)))
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


class JinjaTemplateEvaluator:
    def __init__(self):
        self.environment = jinja2.Environment(
            block_start_string="<%",
            block_end_string="%>",
            variable_start_string="<<",
            variable_end_string=">>",
        )

    def get_evaluator(self, template_str):
        return self.environment.from_string(template_str)

    def evaluate(self, evaluator, funcs, variables):
        return evaluator.render(fake=faker_template_library, **funcs, **variables)


@dataclass
class SimpleValue(FieldDefinition):
    definition: str

    def render(self, context):
        try:
            return context.evaluate(self.definition)
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


def output_batches(output_stream, factories, number, variables):
    context = Context(None, None, output_stream, variables)
    for i in range(0, number):
        for factory in factories:
            factory.generate_rows(output_stream, context)
