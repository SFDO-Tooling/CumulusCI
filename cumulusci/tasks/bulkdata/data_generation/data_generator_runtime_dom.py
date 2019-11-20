from abc import abstractmethod, ABC
from datetime import date
from .data_generator_runtime import (
    Context,
    template_evaluator_factory,
    evaluate_function,
    fix_exception,
)

import jinja2

from .data_gen_exceptions import (
    DataGenError,
    DataGenNameError,
    DataGenSyntaxError,
    DataGenValueError,
)

# objects that represent the hierarchy of a data generator.
# roughly similar to the YAML structure but with domain-specific objects


class ObjectRow:
    """Represents a single row"""

    def __init__(self, sftype, values=()):
        self._sftype = sftype
        self._values = values

    def __getattr__(self, name):
        return self._values[name]


class ObjectTemplate:
    """A factory that generates rows"""

    def __init__(
        self,
        sftype: str,
        filename: str,
        line_num: int,
        count_expr: str = None,
        fields: list = (),
        friends: list = (),
        nickname: str = None,
    ):
        self.sftype = sftype
        self.filename = filename
        self.line_num = line_num
        self.count_expr = count_expr
        self.fields = fields
        self.friends = friends
        self.nickname = nickname
        self.count = None

    def generate_rows(self, storage, parent_context):
        """Generate several rows"""
        context = Context(parent_context, self.sftype)
        self._evaluate_count(context)

        return [self._generate_row(storage, context) for i in range(self.count)]

    def _evaluate_count(self, context):
        if self.count is None:
            if not self.count_expr:
                self.count = 1
            else:
                try:
                    self.count = int(float(self.count_expr.render(context)))
                except (ValueError, TypeError) as e:
                    raise DataGenValueError(
                        f"Cannot evaluate {self.count_expr.definition} as number",
                        self.count_expr.filename,
                        self.count_expr.line_num,
                    ) from e

    def _generate_row(self, storage, context):
        """Generate an individual row"""
        context.incr()
        row = {"id": context.generate_id()}
        sobj = ObjectRow(self.sftype, row)

        context.register_object(sobj, self.nickname)

        context.obj = sobj

        for field in self.fields:
            try:
                row[field.name] = field.generate_value(context)
                assert isinstance(
                    row[field.name], (int, str, bool, date, float, type(None))
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


class StaticEvaluator:
    def __init__(self, definition):
        self.definition = definition

    def __call__(self, context):
        return self.definition


def try_to_infer_type(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        try:
            return int(val)
        except (ValueError, TypeError):
            return val


class FieldDefinition(ABC):
    """Base class for things that render fields"""

    @abstractmethod
    def render(self, context):
        pass

    @property
    def target_table(self):
        return None


class SimpleValue(FieldDefinition):
    """A value with no sub-structure (although it could hold a template)"""

    def __init__(self, definition: str, filename: str, line_num: int):
        self.definition = definition
        self.filename = filename
        self.line_num = line_num
        assert isinstance(filename, str)
        assert isinstance(line_num, int), line_num
        if isinstance(definition, str):
            try:
                self.evaluator = template_evaluator_factory.get_evaluator(definition)
            except Exception as e:
                fix_exception(f"Cannot parse value {self.definition}", self, e)
        else:
            self.evaluator = False

    def render(self, context):
        if self.evaluator:
            try:
                val = self.evaluator(context)
            except jinja2.exceptions.UndefinedError as e:
                raise DataGenNameError(e.message, self.filename, self.line_num) from e
            except Exception as e:
                raise DataGenValueError(str(e), self.filename, self.line_num) from e
        else:
            val = self.definition
        return try_to_infer_type(val)

    def __repr__(self):
        return f"<{self.__class__.__name__ , self.definition}>"


class StructuredValue(FieldDefinition):
    """A value with substructure which will call a handler function."""

    def __init__(self, function_name, args, filename, line_num):
        self.function_name = function_name
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
            value = evaluate_function(func, self.args, self.kwargs, context)
        else:
            try:
                func = context.executable_blocks()[self.function_name]
            except KeyError:
                raise DataGenNameError(
                    f"Cannot find func named {self.function_name}",
                    self.filename,
                    self.line_num,
                )
            value = evaluate_function(func, self.args, self.kwargs, context)

        return value


class ReferenceValue(StructuredValue):
    @property
    def target_table(self):
        return self.args[0].definition


class ChildRecordValue(FieldDefinition):
    """Represents an ObjectRow embedded in another ObjectRow"""

    def __init__(self, sobj: object, filename: str, line_num: int):
        self.sobj = sobj
        self.filename = filename
        self.line_num = line_num

    def render(self, context):
        child_row = self.sobj.generate_rows(context.output_stream, context)[0]
        return child_row["id"]

    @property
    def target_table(self):
        return self.sobj.sftype


class FieldFactory:
    """Represents a single data field (key, value) to be rendered"""

    def __init__(self, name: str, definition: object, filename: str, line_num: int):
        self.name = name
        self.definition = definition
        self.filename = filename
        self.line_num = line_num

    def generate_value(self, context):
        try:
            return self.definition.render(context)
        except Exception as e:
            raise fix_exception(
                f"Problem rendering field {self.name}:\n {str(e)}", self, e
            )

    @property
    def target_table(self):
        return self.definition.target_table

    def __repr__(self):
        return f"<{self.__class__.__name__, self.name, self.definition.__class__.__name__}>"
