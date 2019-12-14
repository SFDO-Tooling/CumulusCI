from abc import abstractmethod, ABC
from datetime import date, datetime
from .data_generator_runtime import evaluate_function, ObjectRow, RuntimeContext
from contextlib import contextmanager
from typing import Union, Dict, Sequence, Optional, cast
from numbers import Number

from fastnumbers import fast_real

import jinja2

from .data_gen_exceptions import (
    DataGenError,
    DataGenNameError,
    DataGenSyntaxError,
    DataGenValueError,
    fix_exception,
)

# objects that represent the hierarchy of a data generator.
# roughly similar to the YAML structure but with domain-specific objects
Scalar = Union[str, Number, date, datetime]
FieldValue = Union[None, Scalar, ObjectRow, tuple]
Definition = Union["ObjectTemplate", "SimpleValue", "StructuredValue"]


class FieldDefinition(ABC):
    """Base class for things that render fields

    Abstract base class for everything that can fulfill the role of X in

    - object: abc
      fields:
         fieldname: X
    """

    def __init__(self):
        self.definition = None
        self.filename = None
        self.line_num = None

    @abstractmethod
    def render(self, context: RuntimeContext) -> FieldValue:
        pass


class ObjectTemplate:
    """A factory that generates rows.

    The runtime equivalent of

    - object: tablename
      count: count_expr   # counts can be dynamic so they are expressions
      fields: list of FieldFactories
      friends: list of other ObjectTemplates
      nickname: string
    """

    def __init__(
        self,
        tablename: str,
        filename: str,
        line_num: int,
        nickname: str = None,
        count_expr: FieldDefinition = None,  # counts can be dynamic so they are expressions
        fields: Sequence = (),
        friends: Sequence = (),
    ):
        self.tablename = tablename
        self.nickname = nickname
        self.count_expr = count_expr
        self.filename = filename
        self.line_num = line_num
        self.fields = fields
        self.friends = friends

    def render(self, context: RuntimeContext) -> Optional[ObjectRow]:
        return self.generate_rows(context.output_stream, context)

    def generate_rows(
        self, storage, parent_context: RuntimeContext
    ) -> Optional[ObjectRow]:
        """Generate several rows"""
        rc = None
        context = RuntimeContext(parent_context, self.tablename)
        count = self._evaluate_count(context)
        with self.exception_handling(f"Cannot generate {self.name}"):
            for i in range(count):
                rc = self._generate_row(storage, context)

        return rc  # return last row

    @contextmanager
    def exception_handling(self, message: str):
        try:
            yield
        except DataGenError:
            raise
        except Exception as e:
            raise DataGenError(f"{message} : {str(e)}", self.filename, self.line_num)

    def _evaluate_count(self, context: RuntimeContext) -> int:
        """Evaluate the count expression to an integer"""
        if not self.count_expr:
            return 1
        else:
            try:
                return int(float(cast(str, self.count_expr.render(context))))
            except (ValueError, TypeError) as e:
                raise DataGenValueError(
                    f"Cannot evaluate {self.count_expr.definition} as number",
                    self.count_expr.filename,
                    self.count_expr.line_num,
                ) from e

    @property
    def name(self) -> str:
        name = self.tablename
        if self.nickname:
            name += f" (self.nickname)"
        return name

    def _generate_row(self, storage, context: RuntimeContext) -> ObjectRow:
        """Generate an individual row"""
        context.incr()
        row = {"id": context.generate_id()}
        sobj = ObjectRow(self.tablename, row)

        context.register_object(sobj, self.nickname)

        context.obj = sobj

        self._generate_fields(context, row)

        try:
            # both of these lines loop over the fields so they could maybe
            # be combined but it kind of messes with the modularity of the
            # code.
            self.register_row_intertable_references(row, context)
            storage.write_row(self.tablename, row)

        except Exception as e:
            raise DataGenError(str(e), self.filename, self.line_num) from e
        for i, childobj in enumerate(self.friends):
            childobj.generate_rows(storage, context)
        return sobj

    def _generate_fields(self, context: RuntimeContext, row: Dict) -> None:
        """Generate all of the fields of a row"""
        for field in self.fields:
            with self.exception_handling(f"Problem rendering value"):
                row[field.name] = field.generate_value(context)
                self._check_type(field, row[field.name], context)
                context.register_field(field.name, row[field.name])

    def _check_type(self, field, generated_value, context: RuntimeContext):
        """Check the type of a field value"""
        allowed_types = (int, str, bool, date, float, type(None), ObjectRow)
        if not isinstance(generated_value, allowed_types):
            raise DataGenValueError(
                f"Field '{field.name}' generated unexpected object: {generated_value} {type(generated_value)}",
                self.filename,
                self.line_num,
            )

    def register_row_intertable_references(
        self, row: dict, context: RuntimeContext
    ) -> None:
        """Before serializing we need to convert objects to flat ID integers."""
        for fieldname, fieldvalue in row.items():
            if isinstance(fieldvalue, ObjectRow):
                context.register_intertable_reference(
                    self.tablename, fieldvalue._tablename, fieldname
                )


class SimpleValue(FieldDefinition):
    """A value with no sub-structure (although it could hold a template)

    - object: abc
      fields:
         fieldname: XXXXX
         fieldname2: <<XXXXX>>
         fieldname3: 42
    """

    def __init__(self, definition: Scalar, filename: str, line_num: int):
        self.filename = filename
        self.line_num = line_num
        self.definition: Scalar = definition
        assert isinstance(filename, str)
        assert isinstance(line_num, int), line_num
        self._evaluator = None

    def evaluator(self, context):
        """Populate the evaluator property once."""
        if self._evaluator is None:
            if isinstance(self.definition, str):
                try:
                    self._evaluator = context.get_evaluator(self.definition)
                except Exception as e:
                    fix_exception(f"Cannot parse value {self.definition}", self, e)
            else:
                self._evaluator = False
        return self._evaluator

    def render(self, context: RuntimeContext) -> FieldValue:
        """Render the value: rendering a template if necessary."""
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
        return fast_real(val) if isinstance(val, str) else val

    def __repr__(self):
        return f"<{self.__class__.__name__ , self.definition}>"


class StructuredValue(FieldDefinition):
    """A value with substructure which will call a handler function.

        - object: abc
          fields:
            fieldname:
                - reference:
                    foo
            fieldname2:
                - random_number:
                    min: 10
                    max: 20
            fieldname3:
                - reference:
                    ...
"""

    def __init__(self, function_name, args, filename, line_num):
        self.function_name = function_name
        self.filename = filename
        self.line_num = line_num
        if isinstance(args, list):  # lists will represent your arguments
            self.args = args
            self.kwargs = {}
        elif isinstance(args, dict):  # dicts will represent named arguments
            self.args = []
            self.kwargs = args
        else:  # scalars will be turned into a one-argument list
            self.args = [args]
            self.kwargs = {}

    def render(self, context: RuntimeContext) -> FieldValue:
        if "." in self.function_name:
            objname, method, *rest = self.function_name.split(".")
            if rest:
                raise DataGenSyntaxError(
                    f"Function names should have only one '.' in them: {self.function_name}",
                    self.filename,
                    self.line_num,
                )
            obj = context.field_vars().get(objname)
            if not obj:
                raise DataGenNameError(
                    f"Cannot find definition for: {objname}",
                    self.filename,
                    self.line_num,
                )

            func = getattr(obj, method)
            if not func:
                raise DataGenNameError(
                    f"Cannot find definition for: {method} on {objname}",
                    self.filename,
                    self.line_num,
                )
            value = evaluate_function(func, self.args, self.kwargs, context)
        else:
            try:
                func = context.executable_blocks()[self.function_name]
            except KeyError:
                raise DataGenNameError(
                    f"Cannot find function named {self.function_name} to handle field value",
                    self.filename,
                    self.line_num,
                )
            value = evaluate_function(func, self.args, self.kwargs, context)

        return value

    def __repr__(self):
        return (
            f"<StructuredValue: {self.function_name} (*{self.args}, **{self.kwargs})>"
        )


class ReferenceValue(StructuredValue):
    """ - object: foo
          fields:
            - reference:
                Y"""


class FieldFactory:
    """Represents a single data field (name, value) to be rendered

    - object:
      fields:
        name: value   # this part
    """

    def __init__(self, name: str, definition: Definition, filename: str, line_num: int):
        self.name = name
        self.filename = filename
        self.line_num = line_num
        self.definition = definition

    def generate_value(self, context) -> FieldValue:
        try:
            return self.definition.render(context)
        except Exception as e:
            raise fix_exception(
                f"Problem rendering field {self.name}:\n {str(e)}", self, e
            )

    def __repr__(self):
        return f"<{self.__class__.__name__, self.name, self.definition.__class__.__name__}>"
