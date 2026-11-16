ALTER TABLE vocab_sets
    ADD COLUMN IF NOT EXISTS text_scaling varchar(7) NOT NULL DEFAULT 'auto'
        CONSTRAINT ck_vocab_sets_text_scaling CHECK (text_scaling IN ('auto', 'minimum')),
    ADD COLUMN IF NOT EXISTS text_vertical_alignment varchar(6) NOT NULL DEFAULT 'center'
        CONSTRAINT ck_vocab_sets_text_vertical_alignment CHECK (text_vertical_alignment IN ('center', 'top'));
