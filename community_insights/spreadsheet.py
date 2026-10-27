"""Tables as an OpenDocument spreadsheet (ODS), one sheet per table."""

import io

from odf.element import Element
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableCell, TableRow
from odf.text import P


def cell(value) -> Element:
    """Numbers stay numbers, so the spreadsheet can calculate with them.

    Args:
        value: A number, a truth value, text or None.

    Returns:
        The cell: a number for numbers and truth values, else text.
    """
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, int | float) and value == value and value not in (float("inf"),):
        return TableCell(valuetype="float", value=value)
    found = TableCell(valuetype="string")
    found.addElement(P(text="" if value is None else str(value)))
    return found


def to_ods(sheets: list[tuple[str, list[dict]]]) -> bytes:
    """[(name, rows)] as an ODS file; each sheet has a header row.

    Args:
        sheets: The sheets as pairs of a name and rows; a name is cut to 31 characters.

    Returns:
        The ODS file.
    """
    document = OpenDocumentSpreadsheet()
    for name, rows in sheets:
        table = Table(name=name[:31])
        columns = list(rows[0]) if rows else ["no data"]
        header = TableRow()
        for column in columns:
            header.addElement(cell(column))
        table.addElement(header)
        for row in rows:
            line = TableRow()
            for column in columns:
                line.addElement(cell(row.get(column)))
            table.addElement(line)
        # odfpy sets the body elements at run time, unknown to the type checker
        document.spreadsheet.addElement(table)  # pyright: ignore[reportAttributeAccessIssue]
    buffer = io.BytesIO()
    document.write(buffer)
    return buffer.getvalue()
