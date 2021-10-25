# -*- coding: utf-8 -*-
"""Format and display CLI output.

Classes:
    CliTable: Pretty prints tabular data to stdout, via Rich's Console API
"""
import os
from typing import List

from rich import box, print
from rich.console import Console
from rich.style import Style
from rich.table import Table

CHECKMARK = "[green]:heavy_check_mark:" if os.name == "posix" else "+"
CROSSMARK = "[red]:cross_mark:" if os.name == "posix" else "-"


class CliTable:
    """Format and print data to the command line in tabular form.
    Attributes:

    * PICTOGRAM_TRUE: True boolean values are replaced with this string.
    * PICTOGRAM_FALSE = False boolean values are replaced with this string.

    Methods:
    * echo: Print the table data to stdout using rich.Console.print
    """

    PICTOGRAM_TRUE = CHECKMARK
    PICTOGRAM_FALSE = " "

    def __init__(self, data, title=None, dim_rows: List[int] = None, **kwargs):
        """Constructor.
        Args:
            data: Required. List[List] of data to format, with the heading as 0-th member.
            title: String to use as the table's title.
            dim_rows: List[int] of row indices to dim.
        """

        data = [self._stringify_row(r) for r in data]
        self._table: Table = Table(*data[0], title=title, box=box.SIMPLE, *kwargs)
        for idx, row in enumerate(data[1:]):
            dim_row = idx + 1 in dim_rows if dim_rows else False
            self._table.add_row(*row, style=Style(dim=dim_row))

    def _stringify_row(self, row: list) -> List[str]:
        stringified_row = []
        for cell in row:
            if isinstance(cell, bool):
                cell = self.PICTOGRAM_TRUE if cell else self.PICTOGRAM_FALSE
            else:
                cell = str(cell)
            stringified_row.append(cell)
        return stringified_row

    def __rich__(self) -> str:
        return self._table

    def echo(self, plain=False, box_style: box.Box = None):
        """Print this table's data using click.echo()."""
        orig_box = self._table.box
        if plain:
            self._table.box = box.ASCII2
        else:
            self._table.box = box_style or orig_box
        console = Console()
        console.print(self._table)
        self._table.box = orig_box

    @property
    def table(self):
        return self._table

    def __str__(self):
        console = Console()
        with console.capture() as capture:
            console.print(self._table)
        return capture.get()


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
            [headings] + [list(map(str, r.values())) for r in results],
        ).echo()
    else:
        return CliTable([["No results"]]).echo()


def _summarize(field):
    if field["referenceTo"]:
        allowed = field["referenceTo"]
    elif field["picklistValues"]:
        allowed = [value["value"] for value in field["picklistValues"]]
    else:
        allowed = field["type"]
    return (field["name"], allowed)


class SimpleSalesforceUIHelpers:
    def __init__(self, sf):
        self._sf = sf

    def query(self, query, format="table", include_deleted=False, max_rows=100):
        """Return the result of a Salesforce SOQL query.

        Arguments:

            * query -- the SOQL query to send to Salesforce, e.g.
                    SELECT Id FROM Lead WHERE Email = "waldo@somewhere.com"
            * include_deleted -- True if deleted records should be included
            * format -- one of these values:
                - "table" -- printable ASCII table (the default)
                - "obj" -- ordinary Python objects
                - "pprint" -- string in easily readable Python dict shape
                - "json" -- JSON
            * max_rows -- maximum rows to output, defaults to 100

        For example:
            query("select Name, Id from Account", format="pprint")
            contact_ids = query("select count(Id) from Contact", format="obj")
        """
        results = self._sf.query_all(query, include_deleted=include_deleted)["records"]

        if len(results) > max_rows:
            truncated = f"... truncated {len(results) - max_rows} rows"
            results = results[0:max_rows]
        else:
            truncated = False

        for result in results:
            if result.get("attributes"):
                del result["attributes"]

        if truncated:
            results.append(truncated)

        if format == "table":
            help_message = "Type help(query) to learn about other return formats or assigning the result."
            print(_soql_table(results, truncated))
            print()
            print(help_message)
            rc = None
        elif format == "obj":
            rc = results
        elif format == "pprint":
            from rich.pretty import pprint

            pprint(results)
            rc = None
        elif format == "json":
            from json import dumps

            rc = dumps(results, indent=2)
        else:
            raise TypeError(f"Unknown format `{format}`")

        return rc

    def describe(self, sobj_name, detailed=False, format="pprint"):
        """Describe an sobject.

        Arguments:

            sobj_name - sobject name to describe. e.g. "Account", "Contact"
            detailed - set to `True` to get detailed information about object
            format -- one of these values:
            - "pprint" -- string in easily readable Python dict shape (default)
            - "obj" -- ordinary Python objects

        For example:

            >>> describe("Account")
            >>> data = describe("Account", detailed=True, format=obj)
        """
        from pprint import pprint

        data = getattr(self._sf, sobj_name).describe()

        if detailed:
            rc = data
        else:
            rc = dict(_summarize(field) for field in data["fields"])

        if format == "pprint":
            pprint(rc)
        elif format == "obj":
            return rc
        else:
            raise TypeError(f"Unknown format {format}")
