"""Render the Khmer faces from sample data into docs/images/khmer-faces.png (and one PNG per face).

Run from the repository root:  .venv/bin/python scripts/render_khmer_faces.py
"""
import time
from pathlib import Path

from PIL import Image

from token_tv.sample import D, H, snapshot
from token_tv.themes import RENDERERS

OUT = Path(__file__).resolve().parents[1] / 'docs' / 'images'
FACES = ('hol', 'bayon', 'sastra')


def sample():
    return snapshot(time.time(), [
        ('claude_a', 'CLAUDE A', 'claude', [('5H', 25, 3 * H + 41 * 60)]),
        ('codex_a', 'CODEX A', 'codex', [('WEEK', 72, 2 * D + 6 * H)]),
        ('grok_a', 'GROK A', 'grok', [('BUDGET', 94, 12 * D + 3 * H)]),
    ])


if __name__ == '__main__':
    sheet = Image.new('RGB', (240 * len(FACES) + 20 * (len(FACES) + 1), 280), '#15110d')
    for i, name in enumerate(FACES):
        image = RENDERERS[name](sample())
        image.save(OUT / f'khmer-{name}.png')
        sheet.paste(image, (20 + i * 260, 20))
    sheet.save(OUT / 'khmer-faces.png')
    print('wrote', ', '.join(f'khmer-{n}.png' for n in FACES), 'and khmer-faces.png')
