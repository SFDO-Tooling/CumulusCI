from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from datetime import date

import jinja2

from cumulusci.core.template_utils import FakerTemplateLibrary, faker_template_library

from .template_funcs import template_funcs


class DataGenError(Exception):
    def __init__(self, message, filename, line_num):
        self.message = message
        self.filename = filename
        self.line_num = line_num
        assert isinstance(filename, str)
        assert isinstance(line_num, int)
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message}\n near {self.filename}:{self.line_num}"


class DataGenSyntaxError(DataGenError):
    pass


class DataGenNameError(DataGenError):
    pass


class DataGenValueError(DataGenError):
    pass


class IdManager:
    """Keep track ofthe most recent ID per Object type"""

    def __init__(self):
        self.last_used_ids = defaultdict(lambda: 0)

    def get_id(self, sobject_name):
        self.last_used_ids[sobject_name] += 1
        return self.last_used_ids[sobject_name]


class CounterGenerator:
    """Generate counters to allow users to make unique text and number fields."""

    def __init__(self, parent=None):
        self.counters = defaultdict(lambda: 0)

    def set_value(self, name, value):
        self.counters[name] = value

    def get_value(self, name):
        return self.counters[name]

    def incr(self, sobject_name):
        self.counters[sobject_name] += 1


class Globals:
    def __init__(self):
        self.named_objects = {}
        self.id_manager = IdManager()
        self.last_seen_obj_of_type = {}

    def register_object(self, obj, nickname=None):
        if nickname:
            self.named_objects[nickname] = obj
        self.last_seen_obj_of_type[obj._sftype] = obj

    def find_object_by_name(self, nickname):
        return self.named_objects[nickname]

    def get_object_id_by_name(self, nickname):
        return self.named_objects[nickname].fields["id"]

    @property
    def object_names(self):
        return {**self.named_objects, **self.last_seen_obj_of_type}


class Context:
    current_id = None
    obj = None
    today = date.today()

    def __init__(self, parent, sobject_name, output_stream=None, options=None):
        self.parent = parent
        self.sobject_name = sobject_name
        if parent:
            self.counter_generator = CounterGenerator(parent.counter_generator)
            self.globals = parent.globals
            self.output_stream = parent.output_stream
            self.options = {**self.parent.options}
        else:  # root Context
            self.counter_generator = CounterGenerator()
            self.globals = Globals()
            self.output_stream = output_stream
            self.options = {**options}

    def incr(self):
        self.counter_generator.incr(self.sobject_name)

    def get_id(self):
        self.current_id = self.globals.id_manager.get_id(self.sobject_name)
        return self.current_id

    def register_object(self, obj, name=None):
        self.obj = obj
        self.globals.register_object(obj, name)

    def evaluate_jinja(self, definition):
        # todo cache templates at compile time and reuse evaluator
        if isinstance(definition, str) and "<<" in definition:
            environment = JinjaTemplateEvaluator()
            evaluator = environment.get_evaluator(definition)

            return environment.evaluate(
                evaluator, options=self.field_vars(), funcs=self.field_funcs()
            )
        else:
            return definition

    def reference(self, x):
        if hasattr(x, "_values"):
            return x.id
        elif isinstance(x, str):
            obj = self.field_vars()[x]
            return obj.id
        else:
            assert 0, f"Can't get reference to {x}"

    evaluate = evaluate_jinja

    def field_vars(self):
        return {
            "id": self.current_id,
            "this": self.obj,
            "today": self.today,
            "fake": faker_template_library,
            "fake_i18n": lambda locale: FakerTemplateLibrary(locale),
            **self.options,
            **self.globals.object_names,
        }

    def field_funcs(self):
        funcs = {name: partial(func, self) for name, func in template_funcs.items()}
        return {
            "number": self.counter_generator.get_value(self.sobject_name),
            "counter": self.counter_generator.get_value,
            "reference": self.reference,
            **funcs,
        }


class SObject:
    def __init__(self, sftype, values=()):
        self._sftype = sftype
        self._values = values

    def __getattr__(self, name):
        return self._values[name]


@dataclass
class SObjectFactory:
    sftype: str
    filename: str
    line_num: int
    count: int = 1
    count_expr: str = None
    fields: list = ()
    friends: list = ()
    nickname: str = None

    def generate_rows(self, storage, parent_context):
        context = Context(parent_context, self.sftype)
        if self.count_expr and self.count is None:
            try:
                self.count = int(float(self.count_expr.render(context)))
            except (ValueError, TypeError):
                raise DataGenValueError(
                    f"Cannot evaluate {self.count_expr.definition} as number",
                    self.filename,
                    self.line_num,
                )
        assert isinstance(self.count, int), self.count
        return [self._generate_row(storage, context) for i in range(self.count)]

    def _generate_row(self, storage, context):
        context.incr()
        row = {"id": context.get_id()}
        sobj = SObject(self.sftype, row)

        context.register_object(sobj, self.nickname)

        context.obj = sobj

        for field in self.fields:
            try:
                row[field.name] = field.generate_value(context)
                assert isinstance(
                    row[field.name], (int, str, bool, date, float)
                ), f"Field '{field.name}' generated unexpected object: {row[field.name]} {type(row[field.name])}"
            except DataGenError as e:
                if not e.filename:
                    e.filename = self.filename
                if not e.line_num:
                    e.line_num = self.line_num

                raise e  # TODO -- add lineno
            except Exception as e:
                raise DataGenError(
                    f"Problem rendering value", self.filename, self.line_num
                ) from e

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

    def evaluate(self, evaluator, funcs, options):
        return evaluator.render(**funcs, **options)


class SimpleValue(FieldDefinition):
    def __init__(self, definition: dict, filename: str, line_num: int):
        self.definition = definition
        self.filename = filename
        self.line_num = line_num
        assert isinstance(filename, str)
        assert isinstance(line_num, int), line_num

    def render(self, context):
        try:
            val = context.evaluate(self.definition)
            try:
                return float(val)
            except ValueError:
                try:
                    return int(val)
                except ValueError:
                    return val
        except jinja2.exceptions.TemplateSyntaxError as e:
            raise DataGenSyntaxError(
                f"Error in parsing {self.definition}: {e}", self.filename, self.line_num
            )
        except jinja2.exceptions.UndefinedError as e:
            raise DataGenNameError(e.message, self.filename, self.line_num)


class StructuredValue(FieldDefinition):
    def __init__(self, function_name, args, filename, line_num):
        self.function_name = function_name
        self.args = args
        self.filename = filename
        self.line_num = line_num
        if isinstance(args, list):
            self.args = args
            self.kwargs = {}
        elif isinstance(args, dict):
            self.args = []
            self.kwargs = args
        else:
            self.args = [args]
            self.kwargs = {}

    def render(self, context):
        if "." in self.function_name:
            objname, method = self.function_name.split(".")
            obj = context.field_vars()[objname]
            value = getattr(obj, method)(*self.args, **self.kwargs)
        else:
            try:
                func = context.field_funcs()[self.function_name]
            except KeyError:
                raise DataGenNameError(
                    f"Cannot find func named {self.function_name}", None, None
                )
            value = func(*self.args, **self.kwargs)

        return value


@dataclass
class ChildRecordValue(FieldDefinition):
    sobj: object
    filename: str
    line_num: int

    def render(self, context):
        child_row = self.sobj.generate_rows(context.output_stream, context)[0]

        return child_row["id"]


@dataclass
class FieldFactory:
    """Represents a single data field (key, value) to be rendered"""

    name: str
    definition: object

    def generate_value(self, context):
        return self.definition.render(context)


def output_batches(output_stream, factories, number, options):
    context = Context(None, None, output_stream, options)
    for i in range(0, number):
        for factory in factories:
            factory.generate_rows(output_stream, context)
