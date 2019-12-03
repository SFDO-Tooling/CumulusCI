from collections import defaultdict, namedtuple
from functools import partial
from datetime import date

from typing import Optional, Dict, List, Sequence, Mapping, Any

import jinja2

from cumulusci.core.template_utils import FakerTemplateLibrary, faker_template_library

from .template_funcs import template_funcs
from .data_gen_exceptions import DataGenError, DataGenSyntaxError


# Runtime objects and algorithms used during the generation of rows.


class IdManager:
    """Keep track of the most recent ID per Object type"""

    def __init__(self):
        self.last_used_ids = defaultdict(lambda: 0)

    def generate_id(self, table_name: str) -> int:
        self.last_used_ids[table_name] += 1
        return self.last_used_ids[table_name]


class CounterGenerator:
    """Generate counters to allow users to make unique text and number fields."""

    def __init__(self, parent=None):
        self.counters = defaultdict(lambda: 0)

    def get_value(self, name: str):
        return self.counters[name]

    def incr(self, name: str):
        self.counters[name] += 1


Dependency = namedtuple(
    "Dependency", ["table_name_from", "table_name_to", "field_name"]
)


class Globals:
    """Globally named objects and other aspects of global scope"""

    def __init__(self):
        self.named_objects = {}
        self.id_manager = IdManager()
        self.last_seen_obj_of_type = {}
        self.intertable_dependencies = set()

    def register_object(self, obj, nickname: str = None):
        """Register an object for lookup by object type and (optionally) Nickname"""
        if nickname:
            self.named_objects[nickname] = obj
        self.last_seen_obj_of_type[obj._tablename] = obj

    @property
    def object_names(self):
        """The globally named objects"""
        return {**self.named_objects, **self.last_seen_obj_of_type}

    def register_intertable_reference(
        self, table_name_from: str, table_name_to: str, fieldname: str
    ):
        self.intertable_dependencies.add(
            Dependency(table_name_from, table_name_to, fieldname)
        )


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
        if "<<" in definition or "<%" in definition:
            try:
                template = self.template_compiler.from_string(definition)
                return DynamicEvaluator(template)
            except jinja2.exceptions.TemplateSyntaxError as e:
                raise DataGenSyntaxError(str(e), None, None) from e
        else:
            return lambda RuntimeRuntimeContext: definition


class RuntimeContext:
    """Current context object. RuntimeContext objects form a linked list-based stack"""

    current_id = None
    obj: Optional["ObjectRow"] = None
    today = date.today()
    template_evaluator_factory = JinjaTemplateEvaluatorFactory()

    def __init__(
        self,
        parent: Optional["RuntimeContext"],
        current_table_name: Optional[str],
        output_stream=None,
        options=None,
    ):
        self.parent = parent
        self.current_table_name = current_table_name
        options = options or {}
        self.field_values: Dict[str, Any] = {}

        if parent:
            self.counter_generator: CounterGenerator = CounterGenerator(
                parent.counter_generator
            )
            self.globals: Globals = parent.globals
            self.output_stream: Any = parent.output_stream
            self.options: Dict = {**parent.options}
        else:  # root RuntimeContext
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

    def register_intertable_reference(self, table_name_from, table_name_to, fieldname):
        self.globals.register_intertable_reference(
            table_name_from, table_name_to, fieldname
        )

    def register_field(self, field_name, field_value):
        """Register each field value to be ready to inject them into template"""
        self.field_values[field_name] = field_value

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
            **self.field_values,
        }

    def field_funcs(self):
        def curry(func):
            rc = partial(func, self)
            if hasattr(func, "lazy"):
                rc.lazy = func.lazy
            return rc

        funcs = {name: curry(func) for name, func in template_funcs.items()}
        return {**funcs}

    def executable_blocks(self):
        return {**self.field_funcs(), "fake": self.fake}

    def fake(self, name):
        return str(getattr(faker_template_library, name))

    def get_evaluator(self, definition: str):
        return self.template_evaluator_factory.get_evaluator(definition)


class DynamicEvaluator:
    def __init__(self, template):
        self.template = template

    def __call__(self, context):
        return self.template.render(**context.field_vars(), **context.field_funcs())


def evaluate_function(func, args: Sequence, kwargs: Mapping, context):
    if not hasattr(func, "lazy"):
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


class ObjectRow:
    """Represents a single row

    Uses __getattr__ so that the template evaluator can use dot-notation."""

    def __init__(self, tablename, values=()):
        self._tablename = tablename
        self._values = values

    def __getattr__(self, name):
        try:
            return self._values[name]
        except KeyError:
            raise AttributeError(name)

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        return f"<ObjectRow {self._tablename} {self.id}>"

    @property
    def _name(self):
        return self._values.get("name")

    def __getstate__(self):
        return self.__dict__


def output_batches(
    output_stream, factories: List, number: int, options: Dict
) -> Globals:
    """Generate 'number' batches to 'output_stream' """
    context = RuntimeContext(None, None, output_stream, options)
    for i in range(0, number):
        for factory in factories:
            factory.generate_rows(output_stream, context)
    return context.globals
