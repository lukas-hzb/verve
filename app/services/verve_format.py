"""Versioned .verve files preserve card content and learning progress."""

import json
from datetime import UTC, datetime

from app.utils.exceptions import InvalidInputError
from app.utils.validators import validate_card_front, validate_card_back, validate_card_level


class VerveFormat:
    @staticmethod
    def dumps(cards, set_name=None):
        records = []
        for card in cards:
            review = VerveFormat._review_time(card['next_review'])
            records.append({
                'front': card['front'], 'back': card['back'], 'level': card['level'],
                'next_review': review.replace(tzinfo=UTC).isoformat().replace('+00:00', 'Z'),
                'last_answer_wrong': card.get('last_answer_wrong', card.get('last_practice_wrong', False)),
            })
        return json.dumps({'format': 'verve', 'version': 1, 'set_name': set_name, 'cards': records},
                          ensure_ascii=False, indent=2) + '\n'

    @staticmethod
    def _review_time(value):
        if not isinstance(value, str):
            raise InvalidInputError('file', 'A Review Date is required')
        try:
            result = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if result.tzinfo is not None:
                result = result.astimezone(UTC).replace(tzinfo=None)
            return result
        except (ValueError, OverflowError):
            raise InvalidInputError('file', 'Invalid Review Date') from None

    @staticmethod
    def loads(content):
        try:
            data = json.loads(content)
        except (ValueError, RecursionError):
            raise InvalidInputError('file', 'Invalid Verve File') from None
        if (not isinstance(data, dict) or data.get('format') != 'verve'
                or type(data.get('version')) is not int or data['version'] != 1
                or not isinstance(data.get('cards'), list)):
            raise InvalidInputError('file', 'Unsupported Verve Format or Version')
        records = []
        seen = set()
        for index, item in enumerate(data['cards']):
            if (not isinstance(item, dict) or type(item.get('level')) is not int
                    or type(item.get('last_answer_wrong', False)) is not bool):
                raise InvalidInputError('file', 'Invalid Card Progress')
            front = validate_card_front(item.get('front'))
            back = validate_card_back(item.get('back'))
            if front in seen:
                raise InvalidInputError('file', 'Duplicate Card Front')
            seen.add(front)
            records.append({
                'front': front, 'back': back,
                'level': validate_card_level(item['level']),
                'next_review': VerveFormat._review_time(item.get('next_review')),
                'last_practice_wrong': item.get('last_answer_wrong', False),
                'shuffle_order': index,
            })
        return records
