"""Versioned .verve files preserve card content and learning progress."""

import json
from datetime import UTC, datetime
from uuid import UUID

from app.utils.exceptions import InvalidInputError
from app.utils.validators import validate_card_source, validate_card_level


class VerveFormat:
    @staticmethod
    def dumps(cards, set_name=None):
        records = []
        for card in cards:
            review = VerveFormat._review_time(card['next_review'])
            records.append({
                'front': card['front'], 'back': card['back'], 'level': card['level'],
                'source_id': card.get('import_key') or card.get('id'),
                'front_format': card.get('front_format', 'plain'),
                'back_format': card.get('back_format', 'plain'),
                'interval_days': card.get('interval_days'),
                'ease_factor': card.get('ease_factor'),
                'next_review': review.replace(tzinfo=UTC).isoformat().replace('+00:00', 'Z'),
                'last_answer_wrong': card.get('last_answer_wrong', card.get('last_practice_wrong', False)),
            })
        return json.dumps({'format': 'verve', 'version': 2, 'set_name': set_name, 'cards': records},
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
                or type(data.get('version')) is not int or data['version'] not in (1, 2)
                or not isinstance(data.get('cards'), list)):
            raise InvalidInputError('file', 'Unsupported Verve Format or Version')
        records = []
        seen = set()
        source_ids = set()
        for index, item in enumerate(data['cards']):
            if (not isinstance(item, dict) or type(item.get('level')) is not int
                    or type(item.get('last_answer_wrong', False)) is not bool):
                raise InvalidInputError('file', 'Invalid Card Progress')
            front_format = item.get('front_format', 'plain')
            back_format = item.get('back_format', 'plain')
            front = validate_card_source(item.get('front'), front_format, front=True)
            back = validate_card_source(item.get('back'), back_format)
            if front in seen:
                raise InvalidInputError('file', 'Duplicate Card Front')
            seen.add(front)
            source_id = item.get('source_id')
            if source_id is not None:
                try:
                    source_id = str(UUID(source_id))
                except (ValueError, AttributeError, TypeError):
                    raise InvalidInputError('file', 'Invalid card ID') from None
                if source_id in source_ids:
                    raise InvalidInputError('file', 'Duplicate card ID')
                source_ids.add(source_id)
            interval = item.get('interval_days')
            ease = item.get('ease_factor')
            if interval is not None and (type(interval) is not int or not 1 <= interval <= 36500):
                raise InvalidInputError('file', 'Invalid review interval')
            if ease is not None and (type(ease) not in (int, float) or not 1.3 <= ease <= 1000):
                raise InvalidInputError('file', 'Invalid ease factor')
            records.append({
                'front': front, 'back': back,
                'front_format': front_format,
                'back_format': back_format,
                'import_key': source_id,
                'interval_days': interval,
                'ease_factor': ease,
                'level': validate_card_level(item['level']),
                'next_review': VerveFormat._review_time(item.get('next_review')),
                'last_practice_wrong': item.get('last_answer_wrong', False),
                'shuffle_order': index,
            })
        return records
