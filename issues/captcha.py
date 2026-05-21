import random
import string
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import base64


def generate_captcha_text(length=6):
    characters = string.ascii_letters + string.digits
    characters = characters.translate(str.maketrans('', '', '0OlI1'))
    return ''.join(random.choices(characters, k=length))


def generate_captcha_image(text):
    width, height = 200, 70

    bg_color = (
        random.randint(220, 255),
        random.randint(220, 255),
        random.randint(220, 255),
    )

    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    for _ in range(200):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(
            random.randint(100, 200),
            random.randint(100, 200),
            random.randint(100, 200),
        ))

    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(
            random.randint(100, 180),
            random.randint(100, 180),
            random.randint(100, 180),
        ), width=1)

    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    x_offset = 10
    for char in text:
        color = (
            random.randint(0, 100),
            random.randint(0, 100),
            random.randint(0, 100),
        )

        char_img = Image.new('RGBA', (40, 60), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_draw.text((5, 5), char, font=font, fill=color)

        angle = random.randint(-25, 25)
        char_img = char_img.rotate(angle, expand=True)

        y_offset = random.randint(5, 20)
        img.paste(char_img, (x_offset, y_offset), char_img)
        x_offset += random.randint(25, 32)

    img = img.filter(ImageFilter.SMOOTH)

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return f"data:image/png;base64,{img_base64}"