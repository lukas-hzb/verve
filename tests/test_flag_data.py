import unittest
from scripts.create_flag_set import flag_cards


class FlagDataTest(unittest.TestCase):
    def test_world_flags_are_unique_complete_and_importable(self):
        from app.services.import_service import ImportService
        from app.utils.validators import validate_card_front, validate_card_back

        cards = flag_cards()
        self.assertEqual(len(cards), 254)
        self.assertEqual(len({front for front, _ in cards}), 254)
        for front, back in cards:
            self.assertTrue(front.startswith('https://flagcdn.com/'))
            self.assertTrue(front.endswith('.svg'))
            validate_card_front(front)
            validate_card_back(back)
            self.assertEqual(len(back.splitlines()), 2)
        by_url = dict(cards)
        self.assertIn('Ciudad de la Paz', by_url['https://flagcdn.com/gq.svg'])
        self.assertIn('Astana', by_url['https://flagcdn.com/kz.svg'])
        self.assertIn('Keine Hauptstadt', by_url['https://flagcdn.com/aq.svg'])
        self.assertIn('Aruba', by_url['https://flagcdn.com/aw.svg'])
        self.assertIn('Wales', by_url['https://flagcdn.com/gb-wls.svg'])
        # A TSV import keeps all cards and escaped within-card line breaks intact.
        content = '\n'.join(front + '\t' + back.replace('\n', r'\n') for front, back in cards)
        imported = ImportService.parse_content(content)
        self.assertEqual(len(imported), 254)
        self.assertEqual(imported[0][0], cards[0][0])
