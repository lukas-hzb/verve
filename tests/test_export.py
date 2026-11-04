import unittest

from app.services.export_service import ExportService, ExportSettingsError
from app.services.import_service import ImportService


class ExportSerializationTests(unittest.TestCase):
    def test_csv_tsv_and_text_round_trip_quotes_multiline_unicode_and_image_links(self):
        cards = [{'front': 'Grüße, "hello"\tbonjour',
                  'back': 'First line\r\nSecond line\nhttps://example.test/image.png'}]
        for file_format, separator in [('csv', ','), ('tsv', '\t'), ('txt', '\t')]:
            with self.subTest(file_format=file_format):
                content = ExportService.serialize(cards, file_format)
                self.assertEqual(ImportService.parse_content(content, '\n', separator),
                                 [(cards[0]['front'], cards[0]['back'])])

    def test_semicolon_csv_and_custom_text_separators_round_trip(self):
        cards = [{'front': 'Dog', 'back': 'Hund'}, {'front': 'Cat', 'back': 'Katze'}]
        for file_format, field, between in [('csv', ';', '\\n'), ('txt', ' -> ', ' || ')]:
            with self.subTest(file_format=file_format):
                content = ExportService.serialize(cards, file_format, field, between)
                self.assertEqual(ImportService.parse_content(content, between, field),
                                 [('Dog', 'Hund'), ('Cat', 'Katze')])

    def test_invalid_or_ambiguous_separators_do_not_silently_lose_content(self):
        for options in [('pdf', None, '\\n'), ('csv', '', '\\n'),
                        ('tsv', ',', '\\n'), ('csv', ',', '|'),
                        ('txt', '|', '||'), ('csv', '"', '\\n'),
                        ('txt', 'Dog', '|')]:
            with self.subTest(options=options), self.assertRaises(ExportSettingsError):
                ExportService.serialize([{'front': 'Dog', 'back': 'Hund'}], *options)

    def test_empty_set_downloads_an_empty_file(self):
        self.assertEqual(ExportService.serialize([]), '')

    def test_utf8_bom_is_not_imported_as_card_text(self):
        self.assertEqual(ImportService.parse_content('\ufeffDog,Hund\n', '\n', ','), [('Dog', 'Hund')])
