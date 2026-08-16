"""Safe avatar image validation and normalization."""

import base64
import io

from PIL import Image, UnidentifiedImageError

from app.utils.exceptions import InvalidInputError


class AvatarService:
    """Convert supported uploads to a small, normalized JPEG data URL."""

    MAX_BYTES = 5 * 1024 * 1024
    MAX_PIXELS = 16_000_000
    ALLOWED_FORMATS = {'JPEG', 'PNG', 'GIF'}

    @classmethod
    def process(cls, avatar_file) -> str:
        raw_image = avatar_file.stream.read(cls.MAX_BYTES + 1)
        if len(raw_image) > cls.MAX_BYTES:
            raise InvalidInputError('avatar', 'Image is too large (max 5 MB)')

        try:
            with Image.open(io.BytesIO(raw_image)) as probe:
                if probe.format not in cls.ALLOWED_FORMATS:
                    raise InvalidInputError('avatar', 'Only JPEG, PNG and GIF images are supported')
                if probe.width * probe.height > cls.MAX_PIXELS:
                    raise InvalidInputError('avatar', 'Image dimensions are too large')
                probe.verify()

            with Image.open(io.BytesIO(raw_image)) as image:
                image.seek(0)
                image.thumbnail((150, 150))
                if image.mode != 'RGB':
                    background = Image.new('RGB', image.size, 'white')
                    if image.mode in ('RGBA', 'LA'):
                        background.paste(image, mask=image.getchannel('A'))
                    else:
                        background.paste(image.convert('RGB'))
                    image = background

                output = io.BytesIO()
                image.save(output, format='JPEG', quality=75, optimize=True)
        except InvalidInputError:
            raise
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
            raise InvalidInputError('avatar', 'The uploaded file is not a valid image')

        encoded = base64.b64encode(output.getvalue()).decode('ascii')
        return f'data:image/jpeg;base64,{encoded}'
