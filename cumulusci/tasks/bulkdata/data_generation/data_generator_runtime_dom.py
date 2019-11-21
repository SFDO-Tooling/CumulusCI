from abc import abstractmethod, ABC
from datetime import date
from .data_generator_runtime import Context, evaluate_function, fix_exception

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
    """Represents a single row

    Uses __getattr__ so that the template evaluator can use dot-notation."""

    def __init__(self, tablename, values=()):
        self._tablename = tablename
        self._values = values

    def __getattr__(self, name):
        return self._values[name]


class ObjectTemplate:
    """A factory that generates rows"""

    def __init__(
        self,
        tablename: str,
        filename: str,
        line_num: int,
        count_expr: str = None,
        fields: list = (),
        friends: list = (),
        nickname: str = None,
    ):
        self.tablename = tablename
        self.filename = filename
        self.line_num = line_num
        self.count_expr = count_expr
        self.fields = fields
        self.friends = friends
        self.nickname = nickname

    def generate_rows(self, storage, parent_context):
        """Generate several rows"""
        context = Context(parent_context, self.tablename)
        count = self._evaluate_count(context)

        return [self._generate_row(storage, context) for i in range(count)]

    def _evaluate_count(self, context):
        if not self.count_expr:
            return 1
        else:
            try:
                return int(float(self.count_expr.render(context)))
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
        sobj = ObjectRow(self.tablename, row)

        context.register_object(sobj, self.nickname)

        context.obj = sobj

        self._generate_fields(context, row)

        try:
            writeable_row = self.replace_objects_with_ids(row, context)
            storage.write_row(self.tablename, writeable_row)

        except Exception as e:
            raise DataGenError(str(e), self.filename, self.line_num) from e
        for i, childobj in enumerate(self.friends):
            childobj.generate_rows(storage, context)
        return sobj

    def _generate_fields(self, context, row):
        """Generate all of the fields of a row"""
        for field in self.fields:
            try:
                row[field.name] = field.generate_value(context)
                self._check_type(field, row[field.name], context)
            except Exception as e:
                raise fix_exception(f"Problem rendering value", self, e) from e

    def _check_type(self, field, generated_value, context):
        allowed_types = (int, str, bool, date, float, type(None), ObjectRow)
        if not isinstance(generated_value, allowed_types):
            raise DataGenValueError(
                f"Field '{field.name}' generated unexpected object: {generated_value} {type(generated_value)}",
                self.filename,
                self.line_num,
            )

    def replace_objects_with_ids(self, row, context):
        writeable_row = {}
        for fieldname, fieldvalue in row.items():
            if isinstance(fieldvalue, ObjectRow):
                writeable_row[fieldname] = fieldvalue.id
                context.register_intertable_reference(
                    self.tablename, fieldvalue._tablename, fieldname
                )
            else:
                writeable_row[fieldname] = fieldvalue

        return writeable_row


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


class SimpleValue(FieldDefinition):
    """A value with no sub-structure (although it could hold a template)"""

    def __init__(self, definition: str, filename: str, line_num: int):
        self.definition = definition
        self.filename = filename
        self.line_num = line_num
        assert isinstance(filename, str)
        assert isinstance(line_num, int), line_num
        self._evaluator = None

    def evaluator(self, context):
        if self._evaluator is None:
            if isinstance(self.definition, str):
                try:
                    self._evaluator = context.template_evaluator_factory.get_evaluator(
                        self.definition
                    )
                except Exception as e:
                    fix_exception(f"Cannot parse value {self.definition}", self, e)
            else:
                self._evaluator = False
        return self._evaluator

    def render(self, context):
        evaluator = self.evaluator(context)
        if evaluator:
            try:
                val = evaluator(context)
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
    pass


class ChildRecordValue(FieldDefinition):
    """Represents an ObjectRow embedded in another ObjectRow"""

    def __init__(self, sobj: object, filename: str, line_num: int):
        self.sobj = sobj
        self.filename = filename
        self.line_num = line_num

    def render(self, context):
        return self.sobj.generate_rows(context.output_stream, context)[0]


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

    def __repr__(self):
        return f"<{self.__class__.__name__, self.name, self.definition.__class__.__name__}>"
