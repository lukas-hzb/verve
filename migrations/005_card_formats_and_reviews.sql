ALTER TABLE cards
    ADD COLUMN IF NOT EXISTS front_format varchar(8) NOT NULL DEFAULT 'plain',
    ADD COLUMN IF NOT EXISTS back_format varchar(8) NOT NULL DEFAULT 'plain',
    ADD COLUMN IF NOT EXISTS import_key varchar(36),
    ADD COLUMN IF NOT EXISTS interval_days integer,
    ADD COLUMN IF NOT EXISTS ease_factor double precision;

CREATE TABLE IF NOT EXISTS card_reviews (
    id varchar(36) PRIMARY KEY,
    card_id varchar(36) NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    reviewed_at timestamp NOT NULL,
    quality integer NOT NULL,
    mode varchar(8) NOT NULL,
    before_state json NOT NULL,
    after_state json NOT NULL,
    undone_at timestamp
);
CREATE INDEX IF NOT EXISTS ix_card_reviews_card_time ON card_reviews (card_id, reviewed_at);
