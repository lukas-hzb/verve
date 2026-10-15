#!/usr/bin/env python3
"""Add the flags standard template and missing private copies for existing users."""

import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print('Use --apply to add the flags standard set. Existing sets and progress are preserved.')
        return

    os.environ['VERCEL'] = '1'
    from app import create_app
    from app.database import db, create_default_vocab_set
    from app.models import User, VocabSet
    from app.services.user_service import UserService
    from sqlalchemy import func

    app = create_app('production')
    with app.app_context():
        create_default_vocab_set()
        added = 0
        try:
            for user in User.query.all():
                if VocabSet.query.filter_by(user_id=user.id).filter(
                    func.lower(func.replace(VocabSet.name, '_', ' ')) == 'flaggen der welt'
                ).first():
                    continue
                UserService.assign_default_vocab_set(user.id, set_names={'Flaggen der Welt'})
                added += 1
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        template = VocabSet.query.filter_by(name='Flaggen der Welt', is_shared=True).one()
        print(f'Flags standard enabled: {template.cards.count()} template cards; {added} new account copies.')


if __name__ == '__main__':
    main()
