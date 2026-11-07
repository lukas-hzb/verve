ALTER TABLE vocab_sets
    ADD COLUMN IF NOT EXISTS text_alignment varchar(6) NOT NULL DEFAULT 'center'
        CONSTRAINT ck_vocab_sets_text_alignment CHECK (text_alignment IN ('left', 'center'));
