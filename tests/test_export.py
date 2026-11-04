import unittest
import json

from app.services.export_service import ExportService, ExportSettingsError
from app.services.import_service import ImportService
from app.services.verve_format import VerveFormat
from app.utils.exceptions import InvalidInputError


class ExportSerializationTests(unittest.TestCase):
    def test_verve_preserves_progress_and_normalizes_dates_to_utc(self):
        source = [{'front': 'Grüße', 'back': 'First\nSecond', 'level': 7,
                   'next_review': '2026-12-03T18:30:00+02:00', 'last_answer_wrong': True}]
        content = ExportService.serialize(source, 'verve', set_name='Languages')
        payload = json.loads(content)
        self.assertEqual(payload['version'], 1)
        self.assertEqual(payload['set_name'], 'Languages')
        self.assertEqual(payload['cards'][0]['next_review'], '2026-12-03T16:30:00Z')
        restored = VerveFormat.loads(content)[0]
        self.assertEqual(restored['level'], 7)
        self.assertEqual(restored['next_review'].isoformat(), '2026-12-03T16:30:00')
        self.assertTrue(restored['last_practice_wrong'])
        self.assertEqual(restored['back'], 'First\nSecond')

    def test_verve_rejects_invalid_versions_and_progress(self):
        base = {'format': 'verve', 'version': 1, 'cards': [
            {'front': 'Dog', 'back': 'Hund', 'level': 2, 'next_review': '2026-12-01T12:00:00Z'}]}
        for change in [{'level': True}, {'level': 0}, {'level': 1001}, {'level': '2'},
                       {'next_review': 'tomorrow'}, {'next_review': None}, {'last_answer_wrong': 'false'}]:
            data = json.loads(json.dumps(base))
            data['cards'][0].update(change)
            with self.subTest(change=change), self.assertRaises(InvalidInputError):
                VerveFormat.loads(json.dumps(data))
        for content in ['invalid', '[]', '{"format":"verve","version":2,"cards":[]}',
                        '{"format":"other","version":1,"cards":[]}']:
            with self.subTest(content=content), self.assertRaises(InvalidInputError):
                VerveFormat.loads(content)

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
