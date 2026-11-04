"""Serialize vocabulary content without changing its learning state."""

import csv
from io import StringIO
from app.services.verve_format import VerveFormat


class ExportSettingsError(ValueError):
    """A safe, user-facing explanation of unsupported export settings."""


class ExportService:
    MIME_TYPES = {'csv': 'text/csv', 'tsv': 'text/tab-separated-values', 'txt': 'text/plain',
                  'verve': 'application/vnd.verve+json'}

    @staticmethod
    def serialize(cards, file_format='verve', field_separator=None, card_separator='\\n', *, set_name=None):
        if file_format == 'verve':
            return VerveFormat.dumps(cards, set_name)
        if file_format not in ExportService.MIME_TYPES:
            raise ExportSettingsError('Choose Verve, CSV, TSV or TXT as the export format.')

        def decode(value):
            return value.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')

        field = decode(field_separator if field_separator is not None else (',' if file_format == 'csv' else '\t'))
        between = decode(card_separator)
        if (not field or not between or len(field) > 16 or len(between) > 16
                or '\0' in field + between or field in between or between in field):
            raise ExportSettingsError('Choose different, non-empty separators of up to 16 characters.')
        if file_format == 'tsv' and field != '\t':
            raise ExportSettingsError('TSV uses a tab between the front and back.')
        if file_format != 'txt' and (len(field) != 1 or field in '\r\n"' or between != '\n'):
            raise ExportSettingsError('CSV and TSV need a single field separator and a line break between cards.')

        rows = [(card['front'], card['back']) for card in cards]
        if between == '\n' and len(field) == 1 and field not in '\r\n"':
            output = StringIO(newline='')
            writer = csv.writer(output, delimiter=field, lineterminator='\r\n')
            writer.writerows(rows)
            return output.getvalue()

        # Custom TXT separators have no quoting convention in the importer.
        if any(field in value or between in value for row in rows for value in row):
            raise ExportSettingsError('A TXT separator occurs in the card text. Choose another separator or export as CSV.')
        return between.join(field.join(row) for row in rows)
