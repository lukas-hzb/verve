#!/usr/bin/env python3
"""Create a private world-flags set for one existing Verve user."""

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def flag_cards():
    records = json.loads((ROOT / 'app/data/world_flags.json').read_text())
    return [(f"https://flagcdn.com/{row['code']}.svg",
             f"{row['country']}\n{row['capital']}") for row in records]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', required=True)
    parser.add_argument('--apply', action='store_true', help='Write the private set; otherwise only validate.')
    args = parser.parse_args()
    cards = flag_cards()
    if not args.apply:
        print(f'Validated {len(cards)} flag cards. No database changes.')
        return

    # Avoid schema creation and shared startup seeds for this targeted data import.
    os.environ['VERCEL'] = '1'
    from app import create_app
    from app.database import db
    from app.models import User, Card, VocabSet
    from app.services.vocab_service import VocabService

    app = create_app('production')
    with app.app_context():
        users = User.query.filter(User.username.ilike(args.username)).all()
        if len(users) != 1:
            raise SystemExit('Expected exactly one matching user; no set created.')
        user = users[0]
        name = 'Flaggen der Welt'
        if VocabSet.query.filter_by(user_id=user.id, name=name).first():
            raise SystemExit('A set with this name already exists; no changes made.')
        try:
            vocab_set = VocabService.create_user_set(user.id, name, commit=False)
            db.session.add_all([Card(vocab_set_id=vocab_set.id, front=front, back=back,
                                     shuffle_order=index) for index, (front, back) in enumerate(cards)])
            db.session.commit()
            assert not vocab_set.is_shared
            print(f'Created {len(cards)} private cards for {user.username}: /set/{vocab_set.id}/overview')
        except Exception:
            db.session.rollback()
            raise


if __name__ == '__main__':
    main()
