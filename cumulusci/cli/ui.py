# -*- coding: utf-8 -*-
"""Format and display CLI output.

Classes:
    CliTable: Pretty prints tabular data to stdout, via click.echo.
"""
import os
import click
import textwrap
from terminaltables import AsciiTable, SingleTable


CHECKMARK = click.style("✔" if os.name == "posix" else "+", fg="green")
CROSSMARK = click.style("✘" if os.name == "posix" else "-", fg="red")


class CliTable:
    """Format and print data to the command line in tabular form.
    Attributes:

    * INNER_BORDER: Boolean passed to terminaltables.inner_row_border. Defaults to True.
    * PICTOGRAM_TRUE: True boolean values are replaced with this string.
    * PICTOGRAM_FALSE = False boolean values are replaced with this string.

    Methods:
    * echo: Print the table data to stdout using click.echo()
    * pretty_table: Table drawn using Unicode drawing characters.
    * ascii_table: Table drawn using Ascii characters.
    """

    INNER_BORDER = True
    PICTOGRAM_TRUE = CHECKMARK
    PICTOGRAM_FALSE = " "

    def __init__(self, data, title=None, wrap_cols=None, bool_cols=None, dim_rows=None):
        """Constructor.
        Args:
            data: Required. List[List] of data to format, with the heading as 0-th member.
            title: String to use as the table's title.
            wrap_cols: List[str] of column names to wrap to max width.
            bool_cols: List[str] of columns containing booleans to stringify.
            dim_rows: List[int] of row indices to dim.
        """
        self._data = data
        self._header = data[0]
        self._title = title
        self._table = SingleTable(self._data, self._title)

        if wrap_cols:
            self._table_wrapper(self._table, wrap_cols)
        if bool_cols:
            for name in bool_cols:
                self.stringify_boolean_col(col_name=name)
        if dim_rows:
            self._dim_row_list(dim_rows)

    def _table_wrapper(self, table, wrap_cols):
        """Query for column width and wrap text"""
        for col_name in wrap_cols:
            index = self._get_index_for_col_name(col_name)
            width = abs(table.column_max_width(index))
            for row in table.table_data:
                row[index] = (
                    textwrap.fill(row[index], width) if row[index] is not None else ""
                )

    def stringify_boolean_col(self, col_name=None, true_str=None, false_str=None):
        """Replace booleans in the given column name with a string.
        Args:

        * col_name: str indicating which columns should be stringifed.
        * true_str: True values will be replaced with this string on posix systems.
        * false_str: False values will be replaced with this string on posix systems.
        """
        col_index = self._get_index_for_col_name(col_name)

        true_str = (
            click.style(true_str, fg="green") if true_str else self.PICTOGRAM_TRUE
        )
        false_str = (
            click.style(false_str, fg="red") if false_str else self.PICTOGRAM_FALSE
        )
        for row in self._table.table_data[1:]:
            row[col_index] = true_str if row[col_index] else false_str

    def echo(self, plain=False):
        """Print this table's data using click.echo().

        Automatically falls back to AsciiTable if there's an encoding error.
        """
        if plain or os.environ.get("TERM") == "dumb":
            table = self.ascii_table()
        else:
            table = str(self)
        click.echo(table)

    def __str__(self):
        try:
            return self.pretty_table()
        except UnicodeEncodeError:
            return self.ascii_table()

    def pretty_table(self):
        """Pretty prints a table."""
        self._table.inner_row_border = self.INNER_BORDER
        return self._table.table + "\n"

    def ascii_table(self):
        """Fallback for dumb terminals."""
        self.plain = AsciiTable(self._table.table_data, self._title)
        self.plain.inner_column_border = False
        self.plain.inner_row_border = False
        return self.plain.table

    def _get_index_for_col_name(self, col_name):
        return self._header.index(col_name)

    def _dim_row_list(self, dim_rows=None):
        """Given a list of integers, iterate over the table data and dim rows.

        Converts each value into a string.
        """
        for row_index in dim_rows:
            if row_index != 0:
                self._table.table_data[row_index] = [
                    self._dim_value(cell) for cell in self._table.table_data[row_index]
                ]

    def _dim_value(self, val):
        """Given an object, convert to a string and wrap using click.style."""
        val = str(val)

        # If a string has been wrapped, wrap each line to avoid dimming table borders
        dimmed_strs = [click.style(line, dim=True) for line in val.split("\n")]
        return "\n".join(dimmed_strs)
