from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from datetime import date

import jinja2

from cumulusci.core.template_utils import FakerTemplateLibrary, faker_template_library

from .template_funcs import template_funcs
from .data_gen_exceptions import (
    DataGenError,
    DataGenNameError,
    DataGenSyntaxError,
    DataGenValueError,
)

# Look in generate_from_yaml for entry points from CCI and command line.
# Look in parse_factory_yaml for the "generate" entry point to the data generation subsystem


class IdManager:
    """Keep track ofthe most recent ID per Object type"""

    def __init__(self):
        self.last_used_ids = defaultdict(lambda: 0)

    def generate_id(self, sobject_name):
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
    """Globally named objects and other aspects of global scope"""

    def __init__(self):
        self.named_objects = {}
        self.id_manager = IdManager()
        self.last_seen_obj_of_type = {}
        self.template_evaluator_factory = JinjaTemplateEvaluatorFactory()

    def register_object(self, obj, nickname=None):
        """Register an object for lookup by object type and (optionally) Nickname"""
        if nickname:
            self.named_objects[nickname] = obj
        self.last_seen_obj_of_type[obj._sftype] = obj

    def find_object_by_nickname(self, nickname):
        return self.named_objects[nickname]

    def get_evaluator(self, definition: str):
        return self.template_evaluator_factory.get_evaluator(definition)

    @property
    def object_names(self):
        """The globally named objects"""
        return {**self.named_objects, **self.last_seen_obj_of_type}


class Context:
    """Current context object. Context objects form a linked list-based stack"""

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
        """Increments the local counter for an object type"""
        self.counter_generator.incr(self.sobject_name)

    def generate_id(self):
        self.current_id = self.globals.id_manager.generate_id(self.sobject_name)
        return self.current_id

    def register_object(self, obj, name=None):
        self.obj = obj
        self.globals.register_object(obj, name)

    def evaluator_for_definition(self, definition):
        return self.globals.get_evaluator(definition)

    def reference(self, x):
        if hasattr(x, "_values"):
            return x.id
        elif isinstance(x, str):
            obj = self.field_vars()[x]
            return obj.id
        else:
            raise DataGenSyntaxError(
                f"Can't get reference to object of type {type(x)}: {x}", None, None
            )

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

    def executable_blocks(self):
        return {**self.field_funcs(), "fake": self.fake}

    def fake(self, name):
        return str(getattr(faker_template_library, name))


class SObject:
    """Represents a single row"""

    def __init__(self, sftype, values=()):
        self._sftype = sftype
        self._values = values

    def __getattr__(self, name):
        return self._values[name]


@dataclass
class SObjectFactory:
    """A factory that generates rows"""

    sftype: str
    filename: str
    line_num: int
    count: int = 1
    count_expr: str = None
    fields: list = ()
    friends: list = ()
    nickname: str = None

    def generate_rows(self, storage, parent_context):
        """Generate several rows"""
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
        if not isinstance(self.count, int):
            raise DataGenValueError(
                f"Count should be an integer not a {type(self.count)} : {self.count}",
                self.filename,
                self.line_num,
            )

        return [self._generate_row(storage, context) for i in range(self.count)]

    def _generate_row(self, storage, context):
        """Generate an individual row"""
        context.incr()
        row = {"id": context.generate_id()}
        sobj = SObject(self.sftype, row)

        context.register_object(sobj, self.nickname)

        context.obj = sobj

        for field in self.fields:
            try:
                row[field.name] = field.generate_value(context)
                assert isinstance(
                    row[field.name], (int, str, bool, date, float)
                ), f"Field '{field.name}' generated unexpected object: {row[field.name]} {type(row[field.name])}"
            except Exception as e:
                raise fix_exception(f"Problem rendering value", self, e) from e

        try:
            storage.write_row(self.sftype, row)
        except Exception as e:
            raise DataGenError(str(e), self.filename, self.line_num) from e
        for i, childobj in enumerate(self.friends):
            childobj.generate_rows(storage, context)
        return row


class FieldDefinition:
    """Base class for things that render fields"""

    def render(self, context):
        pass


class JinjaTemplateEvaluatorFactory:
    def __init__(self):
        self.environment = jinja2.Environment(
            block_start_string="<%",
            block_end_string="%>",
            variable_start_string="<<",
            variable_end_string=">>",
        )

    def get_evaluator(self, definition: str):
        assert isinstance(definition, str), definition
        if "<<" in definition:
            template = self.environment.from_string(definition)
            return lambda context: template.render(
                **context.field_vars(), **context.field_funcs()
            )
        else:
            return lambda context: definition


def try_to_infer_type(val):
    try:
        return float(val)
    except ValueError:
        try:
            return int(val)
        except ValueError:
            return val


class SimpleValue(FieldDefinition):
    """A value with no sub-structure (although it could hold a template)"""

    def __init__(self, definition: dict, filename: str, line_num: int):
        self.definition = definition
        self.filename = filename
        self.line_num = line_num
        assert isinstance(filename, str)
        assert isinstance(line_num, int), line_num
        self._evaluator = None

    def evaluator(self, context, definition):
        """Cache a compiled/instantiated evaluator"""
        if not self._evaluator:
            self._evaluator = context.evaluator_for_definition(definition)
        return self._evaluator

    def render(self, context):
        try:
            if isinstance(self.definition, str):
                evaluator = self.evaluator(context, self.definition)
                val = evaluator(context)
            else:
                val = self.definition
            return try_to_infer_type(val)
        except jinja2.exceptions.TemplateSyntaxError as e:
            raise DataGenSyntaxError(
                f"Error in parsing {self.definition}: {e}", self.filename, self.line_num
            )
        except jinja2.exceptions.UndefinedError as e:
            raise DataGenNameError(e.message, self.filename, self.line_num)


class StructuredValue(FieldDefinition):
    """A value with substructure which will call a handler function."""

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
            objname, method, *rest = self.function_name.split(".")
            if rest:
                raise DataGenSyntaxError(
                    f"Function names should have only one '.' in them: {self.function_name}"
                )
            obj = context.field_vars().get(objname)
            if not obj:
                raise DataGenNameError(f"Cannot find definition for: {objname}")

            func = getattr(obj, method)
            if not func:
                raise DataGenNameError(
                    f"Cannot find definition for: {method} on {objname}"
                )

            value = func(*self.args, **self.kwargs)
        else:
            try:
                func = context.executable_blocks()[self.function_name]
            except KeyError:
                raise DataGenNameError(
                    f"Cannot find func named {self.function_name}", None, None
                )
            value = func(*self.args, **self.kwargs)

        return value


@dataclass
class ChildRecordValue(FieldDefinition):
    """Represents an SObject embedded in another SObject"""

    sobj: object
    filename: str
    line_num: int

    def render(self, context):
        child_row = self.sobj.generate_rows(context.output_stream, context)[0]

        return child_row["id"]


def fix_exception(message, parentobj, e):
    """Add filename and linenumber to an exception if needed"""
    filename, line_num = parentobj.filename, parentobj.line_num
    if isinstance(e, DataGenError):
        if not e.filename:
            e.filename = filename
        if not e.line_num:
            e.line_num = line_num
        raise e
    else:
        raise DataGenError(message, filename, line_num) from e


@dataclass
class FieldFactory:
    """Represents a single data field (key, value) to be rendered"""

    name: str
    definition: object
    filename: str
    line_num: int

    def generate_value(self, context):
        try:
            return self.definition.render(context)
        except Exception as e:
            raise fix_exception(
                f"Problem rendering field {self.name}:\n {str(e)}", self, e
            )


def output_batches(output_stream, factories, number, options):
    """Generate 'number' batches to 'output_stream' """
    context = Context(None, None, output_stream, options)
    for i in range(0, number):
        for factory in factories:
            factory.generate_rows(output_stream, context)
