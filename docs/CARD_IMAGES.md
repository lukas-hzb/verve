# Card Images

Paste a direct HTTPS image URL on its own line on either side of a card:

```text
https://flagcdn.com/de.svg
```

Text and multiple images can be combined on separate lines. For image URLs without a file extension, or to provide alternative text, use:

```text
![Map of Europe](https://example.com/image?id=123)
```

Supported direct URL extensions: SVG, PNG, WebP, JPEG, GIF and AVIF. Images load in the browser without sending a referrer. Use publicly accessible image URLs that allow embedding. Unavailable images show a fallback message.

## Size

The study view displays the complete image at up to 480 × 240 CSS pixels, bounded by the screen and card width. It preserves the aspect ratio and never crops images. Overview thumbnails fit within 72 × 40 pixels to keep rows compact; import previews fit within 160 × 96 pixels.

Use SVG for flags and diagrams. For raster images, about 960 pixels in width is sufficient for sharp display on high-density screens; WebP or PNG under roughly 200 KB keeps loading fast. No manual dimensions are needed.

## World Flags Dataset

The dataset in `app/data/world_flags.json` includes 250 countries and territories plus England, Northern Ireland, Scotland and Wales. It does not include organizations or US states. Each card has a flag on the front and the German country/territory name plus capital or administrative seat on the back. Entries without a capital are marked explicitly.

Sources, checked 2026-10-15:

- [Flagpedia / Flagcdn](https://flagcdn.com/) supplies flag URLs and German names.
- [mledoze/countries](https://github.com/mledoze/countries) supplies country codes, territory coverage and capital names; German capital names reuse Verve's existing dataset where applicable.
- [Equatorial Guinea government](https://www.guineaecuatorialpress.com/index.php/noticias/el_presidente_de_la_republica_proclama_la_ciudad_de_la_paz_como_capital_de_la_republica_de_guinea_ecuatorial_con_la_firma_de_un_decreto_ley) confirms Ciudad de la Paz as the capital since January 2026.
- [Sri Jayewardenepura Kotte municipality](https://www.kotte.mc.gov.lk/index.php?Itemid=175&id=25&lang=en&option=com_content&view=article) confirms Sri Lanka's capital.
- [Nusantara Capital Authority](https://ikn.go.id/id/posts/perpres-nomor-79-tahun-2025-pertegas-kepastian-kelanjutan-dan-penyelesaian-ibu-kota-nusantara) describes the ongoing capital transition in Indonesia.

The adapted country/capital database in `app/data/world_flags.json` is available under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), following [mledoze/countries](https://github.com/mledoze/countries/blob/master/LICENSE). Changes include German names, selected capital corrections and administrative-seat notes, and the four UK constituent countries. Flag images remain hosted by Flagcdn and are separate from this database license.

The dataset is not seeded as a shared set. To create a private copy for one existing user with the configured database:

```sh
python scripts/create_flag_set.py --username Lukas
python scripts/create_flag_set.py --username Lukas --apply
```

The first command validates without accessing the database. The second creates one private set and refuses to overwrite an existing set of the same name. Credentials come from the application's existing environment configuration.
