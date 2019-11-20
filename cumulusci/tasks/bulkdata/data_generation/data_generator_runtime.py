from collections import defaultdict
from functools import partial
from datetime import date

import jinja2

from cumulusci.core.template_utils import FakerTemplateLibrary, faker_template_library

from .template_funcs import template_funcs
from .data_gen_exceptions import DataGenError, DataGenSyntaxError

# Look in generate_from_yaml for entry points from CCI and command line.
# Look in parse_factory_yaml for the "generate" entry point to the data generation subsystem


class IdManager:
    """Keep track of the most recent ID per Object type"""

    def __init__(self):
        self.last_used_ids = defaultdict(lambda: 0)

    def generate_id(self, table_name):
        self.last_used_ids[table_name] += 1
        return self.last_used_ids[table_name]


class CounterGenerator:
    """Generate counters to allow users to make unique text and number fields."""

    def __init__(self, parent=None):
        self.counters = defaultdict(lambda: 0)

    def set_value(self, name, value):
        self.counters[name] = value

    def get_value(self, name):
        return self.counters[name]

    def incr(self, name):
        self.counters[name] += 1


class Globals:
    """Globally named objects and other aspects of global scope"""

    def __init__(self):
        self.named_objects = {}
        self.id_manager = IdManager()
        self.last_seen_obj_of_type = {}
        self.references = {}

    def register_object(self, obj, nickname=None):
        """Register an object for lookup by object type and (optionally) Nickname"""
        if nickname:
            self.named_objects[nickname] = obj
        self.last_seen_obj_of_type[obj._tablename] = obj

    def find_object_by_nickname(self, nickname):
        return self.named_objects[nickname]

    @property
    def object_names(self):
        """The globally named objects"""
        return {**self.named_objects, **self.last_seen_obj_of_type}

    def register_intertable_reference(self, table_name_from, table_name_to):
        self.references.setdefault(table_name_from, set()).add(table_name_to)


class Context:
    """Current context object. Context objects form a linked list-based stack"""

    current_id = None
    obj = None
    today = date.today()

    def __init__(self, parent, current_table_name, output_stream=None, options=None):
        self.parent = parent
        self.current_table_name = current_table_name

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
        self.counter_generator.incr(self.current_table_name)

    def generate_id(self):
        self.current_id = self.globals.id_manager.generate_id(self.current_table_name)
        return self.current_id

    def register_object(self, obj, name=None):
        self.obj = obj
        self.globals.register_object(obj, name)

    def register_intertable_reference(self, table_name_to):
        self.globals.register_intertable_reference(
            self.current_table_name, table_name_to
        )

    def field_vars(self):
        return {
            "id": self.current_id,
            "this": self.obj,
            "today": self.today,
            "fake": faker_template_library,
            "fake_i18n": lambda locale: FakerTemplateLibrary(locale),
            "number": self.counter_generator.get_value(self.current_table_name),
            **self.options,
            **self.globals.object_names,
        }

    def field_funcs(self):
        funcs = {name: partial(func, self) for name, func in template_funcs.items()}
        return {**funcs}

    def executable_blocks(self):
        return {**self.field_funcs(), "fake": self.fake}

    def fake(self, name):
        return str(getattr(faker_template_library, name))


class StaticEvaluator:
    def __init__(self, definition):
        self.definition = definition

    def __call__(self, context):
        return self.definition


class DynamicEvaluator:
    def __init__(self, template):
        self.template = template

    def __call__(self, context):
        return self.template.render(**context.field_vars(), **context.field_funcs())


class JinjaTemplateEvaluatorFactory:
    def __init__(self):
        self.template_compiler = jinja2.Environment(
            block_start_string="<%",
            block_end_string="%>",
            variable_start_string="<<",
            variable_end_string=">>",
        )

    def get_evaluator(self, definition: str):
        assert isinstance(definition, str), definition
        if "<<" in definition:
            try:
                template = self.template_compiler.from_string(definition)
                return DynamicEvaluator(template)
            except jinja2.exceptions.TemplateSyntaxError as e:
                raise DataGenSyntaxError(str(e), None, None) from e
        else:
            return lambda context: definition


template_evaluator_factory = JinjaTemplateEvaluatorFactory()


def try_to_infer_type(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        try:
            return int(val)
        except (ValueError, TypeError):
            return val


def evaluate_function(func, args, kwargs, context):
    args = [arg.render(context) if hasattr(arg, "render") else arg for arg in args]
    kwargs = {
        name: arg.render(context) if hasattr(arg, "render") else arg
        for name, arg in kwargs.items()
    }
    value = func(*args, **kwargs)
    return value


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


def output_batches(output_stream, factories, number, options):
    """Generate 'number' batches to 'output_stream' """
    context = Context(None, None, output_stream, options)
    for i in range(0, number):
        for factory in factories:
            factory.generate_rows(output_stream, context)
