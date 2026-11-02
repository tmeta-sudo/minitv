"""Angkor: a Khmer-inspired clock face.

A dusk sky behind the five towers of Angkor Wat, temple-gold frames with stepped corners and
lotus-bud ornaments, and the used percentage in Khmer numerals (០១២៣៤៥៦៧៨៩).

The meaning of every value is unchanged: used %, the window name, the reset time, OLD for an
old reading and a dash (never 0) when nothing was reported. The temple is drawn from shapes only.
"""
import functools
import math

from PIL import Image, ImageDraw

from token_tv.display import account_label, fit_text, overview_rows, reading, shown_windows, slots
from token_tv.themes import BANDS, SIZE, Canvas, band, bot_sprite, face, gauge, mix, number_text, place_bot, rgb

SKY = ((0.00, '#140a35'), (0.38, '#4b1760'), (0.62, '#b0306a'), (0.82, '#f2762e'), (1.00, '#ffc247'))
GOLD, GOLD_DEEP, CREAM, STONE = '#f4c14e', '#a8741d', '#fff1cf', '#0d0714'
KHMER_DIGITS = str.maketrans('0123456789', '០១២៣៤៥៦៧៨៩')


def khmer_number(used):
    """The used percentage in Khmer numerals; a dash when nothing was reported."""
    return number_text(used).translate(KHMER_DIGITS)


def lerp_stops(stops, t):
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if t <= b:
            return mix(ca, cb, (t - a) / (b - a))
    return rgb(stops[-1][1])


def prang_profile(t):
    """Half-width of a tower at height t (0 base .. 1 tip): stepped tiers, then a lotus-bud spire."""
    if t < 0.34:  # three receding terraces
        return 1.0 - 0.17 * int(t / 0.34 * 3) / 1.0 * 1.0 - 0.0
    u = (t - 0.34) / 0.66
    return 0.62 * (1 - u ** 1.7) ** 0.62 * (1 + 0.22 * math.sin(u * math.pi * 1.3))


def tower(draw, cx, base, height, width, scale):
    """One prang: terraces below, a lotus-bud spire above, as a single filled outline (4× scale)."""
    steps = 90
    right = []
    for i in range(steps + 1):
        t = i / steps
        right.append((cx + prang_profile(t) * width / 2 * scale, base - t * height * scale))
    left = [(2 * cx - x, y) for x, y in reversed(right)]
    draw.polygon(right + left, fill=STONE)
    # a finial needle
    top = base - height * scale
    draw.line((cx, top, cx, top - 0.16 * height * scale), fill=STONE, width=max(2, round(scale)))


@functools.lru_cache(maxsize=None)
def backdrop():
    """Sky, sun and the silhouette of Angkor Wat, drawn once at 4× and reduced for clean edges."""
    s = 4
    big = Image.new('RGB', (SIZE * s, SIZE * s))
    px = ImageDraw.Draw(big)
    for y in range(SIZE * s):
        px.line((0, y, SIZE * s, y), fill=lerp_stops(SKY, y / (SIZE * s)))
    horizon = 214 * s
    # the sun, set behind the central tower, and a soft halo
    cx = 120 * s
    for r, alpha in ((74, .10), (60, .16), (48, .24)):
        halo = Image.new('RGBA', big.size, (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse((cx - r * s, horizon - 36 * s - r * s, cx + r * s, horizon - 36 * s + r * s),
                                     fill=(255, 205, 90, round(alpha * 255)))
        big.paste(halo, (0, 0), halo)
    px = ImageDraw.Draw(big)
    sun = 34 * s
    px.ellipse((cx - sun, horizon - 36 * s - sun, cx + sun, horizon - 36 * s + sun), fill=(255, 226, 140))
    # temple: long gallery, then towers (centre tallest), then a causeway to the bottom
    px.rectangle((14 * s, horizon - 12 * s, 226 * s, horizon + 2 * s), fill=STONE)
    for i in range(18):  # the gallery's pillars
        x = (22 + i * 11.4) * s
        px.rectangle((x, horizon - 17 * s, x + 4 * s, horizon - 12 * s), fill=STONE)
    for x, h, w in ((120, 74, 34), (92, 54, 26), (148, 54, 26), (66, 36, 20), (174, 36, 20)):
        tower(px, x * s, horizon - 10 * s, h, w, s)
    px.rectangle((0, horizon + 1 * s, SIZE * s, SIZE * s), fill=STONE)
    # the moat: a faint reflection of the sky under the temple
    glow = Image.new('RGBA', big.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for y in range(horizon + 4 * s, SIZE * s, s * 3):
        t = (y - horizon) / (SIZE * s - horizon)
        gd.line((60 * s, y, 180 * s, y), fill=(244, 160, 70, round(60 * (1 - t))), width=s)
    big.paste(glow, (0, 0), glow)
    return big.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def lotus(draw, cx, cy, size, fill):
    """A small lotus bud: three pointed petals."""
    for dx, lean in ((-1, -0.55), (1, 0.55), (0, 0)):
        draw.polygon([(cx, cy), (cx + dx * size * 0.55, cy - size * 0.55),
                      (cx + lean * size * 0.4, cy - size * 1.15)], fill=fill)


def frame(draw, box, step=5):
    """A gold frame with stepped (temple-terrace) corners and a lotus bud on the top edge."""
    x0, y0, x1, y1 = box
    outline = [(x0 + step, y0), (x1 - step, y0), (x1 - step, y0 + step), (x1, y0 + step), (x1, y1 - step),
               (x1 - step, y1 - step), (x1 - step, y1), (x0 + step, y1), (x0 + step, y1 - step), (x0, y1 - step),
               (x0, y0 + step), (x0 + step, y0 + step), (x0 + step, y0)]
    draw.polygon(outline, fill=(13, 7, 20, 96))
    draw.line(outline + [outline[0]], fill=GOLD, width=1, joint='curve')
    inner = [(x0 + step + 3, y0 + 3), (x1 - step - 3, y0 + 3), (x1 - step - 3, y0 + step + 3), (x1 - 3, y0 + step + 3),
             (x1 - 3, y1 - step - 3), (x1 - step - 3, y1 - step - 3), (x1 - step - 3, y1 - 3), (x0 + step + 3, y1 - 3),
             (x0 + step + 3, y1 - step - 3), (x0 + 3, y1 - step - 3), (x0 + 3, y0 + step + 3),
             (x0 + step + 3, y0 + step + 3), (x0 + step + 3, y0 + 3)]
    draw.line(inner + [inner[0]], fill=GOLD_DEEP, width=1)


def render_angkor(snapshot):
    cv = Canvas('#000000')
    cv.base.paste(backdrop().convert('RGBA'), (0, 0))
    label = lambda size: face('chakra-petch-700.woff2', size)
    khmer = lambda size: face('noto-sans-khmer-700.woff2', size)
    rows = overview_rows(snapshot)
    for sl, row in zip(slots(len(rows), top=3, pitch=79, height=75), rows):
        y, h, at = sl.y, sl.h, sl.at
        wins = shown_windows(row, sl.count)
        used, period, old, reset = reading(row, wins[0] if wins else None)  # None: no reading, never 0
        x0, x1 = 4, 235
        frame(cv.draw, (x0, y, x1, y + h - 1))
        bw, bh = round(24 * sl.icon), round(20 * sl.icon)
        bot = (13, y + 8 if sl.count == 1 else at(8), bw, bh)
        place_bot(cv.ink, bot_sprite(row['provider'], bw, bh), bot)
        note = ('OLD ' if old else '') + period if sl.count < 4 else ('OLD' if old else '')
        tsize = sl.txt(10)
        room = 226 - (bw + 22) - (cv.draw.textlength(note, font=label(tsize)) + 10 if note else 0)
        cv.text((bw + 22, bot[1] + bh / 2), fit_text(cv.draw, account_label(row), label(tsize), room), label(tsize),
                CREAM, anchor='lm')
        cv.text((226, bot[1] + bh / 2), note, label(tsize), '#ff9f6b' if old else GOLD, anchor='rm')
        # the used percentage in Khmer numerals; the digits' glow keeps them readable on the sky
        nsize = sl.num(34)
        number = khmer_number(used)
        ny = at(60) - round(14 * sl.k) if sl.count > 1 else y + h - 34
        cv.text((14, ny), number, khmer(nsize), CREAM, glow=rgb(GOLD) + (120,), anchor='ls')
        if used is not None:
            nx = 14 + cv.draw.textlength(number, font=khmer(nsize)) + 3
            cv.text((nx, ny), '%', label(sl.num(15)), GOLD, anchor='ls')
        if sl.count < 4:
            cv.text((226, ny - sl.txt(15) - 2), 'RESET', label(sl.txt(7)), GOLD, anchor='rs')
        cv.text((226, ny), reset, label(sl.txt(17)), CREAM, anchor='rs')
        gy = y + h - 16 if sl.count == 1 else at(60)
        gauge(cv, (14, gy, 226, gy + max(5, round(7 * min(sl.k, 1.3)))), used, band('retro', used or 0), gap=2,
              track=(255, 241, 207, 45), empty=(255, 241, 207, 90), stale=old, shade=True)
    return cv.finish(blur=2)
