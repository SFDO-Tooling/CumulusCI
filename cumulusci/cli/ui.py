"""Format and display CLI output.

Classes:
    CliTable: Pretty prints tabluar data to stdout, via click.echo.
"""
import os
import collections
import click
import textwrap
from terminaltables import AsciiTable, SingleTable


class CliTable:
    """Format and print data to the command line in tabular form.
    Attributes:
        INNER_BORDER: Boolean passed to terminaltables.inner_row_border. Defaults to True.
        PICTOGRAM_TRUE: True boolean values are replaced with this string.
        PICTOGRAM_FALSE = False boolean values are replaced with this string.
    Methods:
        echo: Print the table data to stdout using click.echo()
        pretty_table: Table drawn using Unicode drawing characters.
        ascii_table: Table drawn using Ascii characters.
    """

    INNER_BORDER = True
    PICTOGRAM_TRUE = click.style("✔" if os.name == "posix" else "+", fg="green")
    PICTOGRAM_FALSE = click.style("✘" if os.name == "posix" else "-", fg="red")

    def __init__(self, data, title=None, wrap_cols=None):
        """Constructor.
        Args:
            data: Required. List[List] of data to format, with the heading as 0-th member.
            title: String to use as the table's title.
            wrap_cols: List[int] of column indices to wrap to max width.

        """
        self._data = data
        self._title = title
        self.table = SingleTable(self._data, self._title)
        if wrap_cols:
            self._table_wrapper(self.table, wrap_cols)

    def _table_wrapper(self, table, wrap_cols):
        """Query for column width and wrap text"""
        for index in wrap_cols:
            width = abs(table.column_max_width(index))
            for row in table.table_data:
                row[index] = (
                    textwrap.fill(row[index], width) if row[index] is not None else ""
                )

    def stringify_boolean_cols(self, col_index=None):
        """Replace a boolean at the given index with a checkmark.
        Args:
            col_index: List[int] or int indicating which columns should be stringifed.
        """
        col_index = (
            col_index if isinstance(col_index, collections.Iterable) else [col_index]
        )
        for row in self.table.table_data[1:]:
            for index in col_index:
                row[index] = self.PICTOGRAM_TRUE if row[index] else self.PICTOGRAM_FALSE

    def echo(self, plain=False):
        """Print this tables data using click.echo().

        Automatically falls back to AsciiTable if there's an encoding error.
        """
        if plain:
            self.ascii_table()
            return None

        try:
            self.pretty_table()
        except UnicodeEncodeError:
            self.ascii_table()

        click.echo("\n")

    def pretty_table(self):
        """Pretty prints a table."""
        self.table.inner_row_border = self.INNER_BORDER
        click.echo(self.table.table)

    def ascii_table(self):
        """Fallback for dumb terminals."""
        self.plain = AsciiTable(self.table.table_data, self._title)
        self.plain.inner_row_border = self.INNER_BORDER
        click.echo(self.plain.table)
