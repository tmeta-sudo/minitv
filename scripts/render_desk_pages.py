"""Render the desk pages for the docs into docs/images/desk-pages.png, from examples/desk/ and a fixed moment.

Run from the repository root:  .venv/bin/python scripts/render_desk_pages.py
"""
import datetime
from pathlib import Path

from PIL import Image

from token_tv import desk

ROOT = Path(__file__).resolve().parents[1]


if __name__ == '__main__':
    config = desk.load_config(ROOT / 'examples' / 'desk' / 'desk.json')
    moment = datetime.datetime(2026, 11, 2, 10, 51, tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
    board = Path(config['pages'][3]['file'])
    now = board.stat().st_mtime + 60  # the board was written a minute ago
    pages = [desk.render_page(page, moment, now) for page in config['pages']]
    sheet = Image.new('RGB', (240 * len(pages) + 20 * (len(pages) + 1), 280), '#15110d')
    for i, image in enumerate(pages):
        sheet.paste(image, (20 + i * 260, 20))
    sheet.save(ROOT / 'docs' / 'images' / 'desk-pages.png')
    print('wrote docs/images/desk-pages.png')
