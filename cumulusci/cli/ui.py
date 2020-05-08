# -*- coding: utf-8 -*-
"""Format and display CLI output.

Classes:
    CliTable: Pretty prints tabular data to stdout, via click.echo.
"""
import os
import click
import textwrap
import shutil
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


def pretty_soql_query(sf, query, include_deleted=False, format="obj", max_rows=100):
    """Return the result of a Salesforce SOQL query.

        Arguments:

        * query -- the SOQL query to send to Salesforce, e.g.
                   SELECT Id FROM Lead WHERE Email = "waldo@somewhere.com"
        * include_deleted -- True if deleted records should be included
        * format -- one of these values:
           - obj -- ordinary Python objects (default)
           - table -- printable ASCII tablee
           - pprint -- string in easily readable Python dict shape
           - json -- JSON
        * max_rows -- maximuim rows to output, defaults to 100

    For example:
        pretty_soql_query("select Name, Id from Account")
        pretty_soql_query("select count(Id) from Contact")
    """
    results = sf.query(query, include_deleted=include_deleted)["records"]

    if len(results) > max_rows:
        truncated = f"... truncated {len(results) - max_rows} rows"
        results = results[0:max_rows]
    else:
        truncated = False

    for result in results:
        print(result)
        del result["attributes"]

    if truncated:
        results.append(truncated)

    if format == "table":
        return _soql_table(results, truncated)
    if format == "obj":
        return results
    elif format == "pprint":
        return _pformat(results)
    elif format == "json":
        from json import dumps

        return dumps(results, indent=2)
    else:
        raise TypeError(f"Unknown format `{format}`")


def _soql_table(results, truncated):
    if results:
        if truncated:
            assert results[-1] == truncated
            first_row = results[0]
            fake_row = {k: "" for k, v in first_row.items()}
            first_column = list(first_row)[0]
            fake_row[first_column] = truncated

            results[-1] = fake_row

        headings = list(results[0].keys())
        return CliTable(
            [headings] + [list(r.values()) for r in results], wrap_cols=headings
        )
    else:
        return CliTable([["No results"]])


def _pformat(values):
    columns, _rows = shutil.get_terminal_size(fallback=(80, 24))
    from pprint import pformat

    return pformat(values)


def pretty_describe(sf, sobj_name, detailed=False):
    """Describe an sobject. Use detailed=True to get lots of details"""
    data = getattr(sf, sobj_name).describe()

    if detailed:
        rc = data
    else:
        rc = [_summarize(field) for field in data["fields"]]

    return _pformat(rc)


def _summarize(field):
    if field["referenceTo"]:
        allowed = field["referenceTo"]
    elif field["picklistValues"]:
        allowed = [value["value"] for value in field["picklistValues"]]
    else:
        allowed = field["type"]
    return (field["name"], allowed)
