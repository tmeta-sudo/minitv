"""Three Khmer clock faces made from Cambodian craft rather than from pictures of it.

* hol    – a silk sampot hol: ikat bands woven in natural dyes, their edges feathered the way
           resist-dyed thread really blurs.
* bayon  – carved sandstone: a weathered stone wall, recessed panels, engraved type, inlaid gauges.
* sastra – a palm-leaf manuscript (sastra slek rit): leaf strips on a cord, text incised and inked.
* kbach  – gold ornament on lacquer: a kbach vine of curls and flame leaves between the rows (token_tv/kbach.py).

The used percentage is written in Khmer numerals (០១២៣៤៥៦៧៨៩) and the reset time in Khmer words
(ថ្ងៃ day, ម៉ោង hour, នាទី minute) when the machine can shape Khmer script; otherwise Latin letters.
Everything else keeps its meaning: window name, `OLD` for an old reading, a dash (never 0) for none.
"""
import functools
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, features

from token_tv.display import account_label, fit_text, overview_rows, reading, shown_windows, slots
from token_tv import kbach
from token_tv.themes import SIZE, Canvas, face, glyph, mix, number_text, rgb

SHAPING = features.check('raqm')  # Khmer vowels and subscripts need it; the digits do not
DIGITS = str.maketrans('0123456789', '០១២៣៤៥៦៧៨៩')
UNITS = {'d': 'ថ្ងៃ', 'h': 'ម៉ោង', 'm': 'នាទី'}


def khmer_number(used):
    """The used percentage in Khmer numerals; '--' when nothing was reported."""
    return number_text(used).translate(DIGITS)


def khmer_time(reset):
    """'2d 6h' as '២ថ្ងៃ ៦ម៉ោង'; unchanged when unknown ('--') or when Khmer cannot be shaped here."""
    if not SHAPING:
        return reset
    parts = []
    for token in reset.split():
        if token[-1:] not in UNITS or not token[:-1].isdigit():
            return reset
        parts.append((int(token[:-1]), token[:-1].translate(DIGITS) + UNITS[token[-1]]))
    kept = [text for value, text in parts if value] or [parts[0][1]] if parts else []
    return ' '.join(kept) or reset


def latin(size, weight=700):
    return face('manrope.ttf', size, weight)


def level_color(colors, used):
    """One colour of four for below 50, 50–79, 80–89 and 90–100 % (a missing reading has none)."""
    return colors[0 if used < 50 else 1 if used < 80 else 2 if used < 90 else 3]


def numeral(cv, x, base, used, font, fill):
    """Khmer numerals sitting on `base`; a missing reading is a drawn bar. Returns the right edge."""
    if used is None:
        size = font.size
        top = base - round(size * .32)
        cv.draw.rectangle((x, top, x + round(size * .5), top + max(2, round(size * .09))), fill=fill)
        return x + round(size * .5)
    text = khmer_number(used)
    cv.text((x, base), text, font, fill, anchor='ls')
    return x + cv.draw.textlength(text, font=font)


def entries(snapshot):
    """Each row with its place and the one window it shows: (slot, row, used, tag, old, reset)."""
    data = overview_rows(snapshot)
    for sl, row in zip(slots(len(data), top=3, pitch=79, height=75), data):
        wins = shown_windows(row, sl.count)
        used, period, old, reset = reading(row, wins[0] if wins else None)  # used is None: no reading, never 0
        tag = ('OLD' if old else '') if sl.count == 4 else ('OLD ' if old else '') + period
        yield sl, row, used, tag.strip(), old, reset


def stale_hatch(draw, box, color, step=4):
    x0, y0, x1, y1 = box
    for k in range(-(y1 - y0), x1 - x0, step):
        draw.line((x0 + k, y1, x0 + k + (y1 - y0), y0), fill=color, width=1)


def feather(layer, seed, blur=.7):
    """Ikat's signature: resist-dyed thread never lines up, so every pattern edge breathes sideways."""
    rnd = random.Random(seed)
    out = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    for y in range(layer.height):
        out.paste(layer.crop((0, y, layer.width, y + 1)), (rnd.choice((-1, 0, 0, 1)), y))
    return out.filter(ImageFilter.GaussianBlur(blur))


# ───────────────────────────── Hol: ikat silk ─────────────────────────────

INDIGO, MADDER, TURMERIC, CREAM, HOL_INK = '#16203b', '#a63a2c', '#dba43f', '#f0e4c8', '#0e1628'
HOL_LEVELS = ('#5b9a94', '#dba43f', '#d4682f', '#c43b31')
STRIP = 9


@functools.lru_cache(maxsize=None)
def hol_base(count):
    rnd = random.Random(11)
    warp = [rnd.randint(-5, 5) for _ in range(SIZE)]
    base = rgb(INDIGO)
    image = Image.new('RGB', (SIZE, SIZE))
    px = image.load()
    for y in range(SIZE):
        weft = 3 if y % 2 == 0 else 0  # the weave: threads over, threads under
        for x in range(SIZE):
            d = warp[x] + weft
            px[x, y] = (max(0, base[0] + d), max(0, base[1] + d), max(0, base[2] + d + 2))
    motif = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(motif)
    for sl in slots(count, top=3, pitch=79, height=75):
        y0 = sl.y + sl.h - STRIP
        draw.rectangle((0, y0, SIZE, y0 + STRIP - 1), fill=MADDER)
        draw.rectangle((0, y0, SIZE, y0), fill=CREAM)
        draw.rectangle((0, y0 + STRIP - 1, SIZE, y0 + STRIP - 1), fill=CREAM)
        cy = y0 + STRIP // 2
        for i, cx in enumerate(range(4, SIZE + 8, 10)):  # a chain of lozenges, each with a seed at its heart
            colour = CREAM if i % 2 == 0 else TURMERIC
            draw.polygon([(cx, cy - 3), (cx + 5, cy), (cx, cy + 3), (cx - 5, cy)], fill=colour)
            draw.rectangle((cx, cy, cx, cy), fill=MADDER)
    image = image.convert('RGBA')
    image.alpha_composite(feather(motif, 3))
    return image


def render_hol(snapshot):
    cv = Canvas('#000000')
    cv.base.paste(hol_base(len(overview_rows(snapshot))), (0, 0))
    for sl, row, used, tag, old, reset in entries(snapshot):
        y, ch = sl.y, sl.h - STRIP
        # provider mark and name
        mark = max(10, round(12 * sl.small))
        cv.ink.alpha_composite(glyph(row['provider'], mark, TURMERIC), (14, round(y + ch * .17 - mark / 2 + 2)))
        size = sl.txt(10)
        room = 226 - (30 + (cv.draw.textlength(tag, font=latin(size)) + 12 if tag else 0))
        cv.spaced((14 + mark + 6, round(y + ch * .17 + 2)), fit_text(cv.draw, account_label(row), latin(size), room).upper(),
                  latin(size), CREAM, 1.2, anchor='lm')
        cv.spaced((226, round(y + ch * .17 + 2)), tag, latin(size), '#f4b36a' if old else TURMERIC, 1.2, anchor='rm')
        # the number, in heavy Moul, and the time to the reset
        base = round(y + ch * .74)
        nfont = face('moul.woff2', min(sl.num(26), 42))
        right = numeral(cv, 14, base, used, nfont, CREAM)
        if used is not None:
            cv.text((right + 3, base), '%', latin(sl.num(14), 800), TURMERIC, anchor='ls')
        # the gauge: ten woven blocks
        gh = max(5, round(7 * min(sl.k, 1.5)))
        gy = round(y + ch - gh - 2)
        tfont = face('battambang-700.woff2', min(sl.txt(17), 18))
        cv.text((226, base if sl.count > 1 else gy - 12), khmer_time(reset), tfont, CREAM, anchor='rs')
        cell, gap = (212 - 9 * 3) / 10, 3
        for i in range(10):
            a = 14 + i * (cell + gap)
            box = (round(a), gy, round(a + cell) - 1, gy + gh - 1)
            cv.draw.rectangle(box, fill='#232f55')
            if used is None:
                for dx in range(box[0], box[2] + 1, 3):
                    cv.draw.point((dx, box[1]), fill='#53608a')
                    cv.draw.point((dx, box[3]), fill='#53608a')
                continue
            frac = max(0, min(1, used / 10 - i))
            if frac <= 0:
                continue
            fill = level_color(HOL_LEVELS, used)
            fb = (box[0], box[1], max(box[0], round(a + cell * frac) - 1), box[3])
            cv.draw.rectangle(fb, fill=fill)
            for yy in range(fb[1] + 1, fb[3] + 1, 2):  # weft lines over the dyed block
                cv.draw.line((fb[0], yy, fb[2], yy), fill=mix(fill, HOL_INK, .28))
            if old:
                stale_hatch(cv.draw, fb, '#232f55')
    return cv.finish(blur=1)


# ─────────────────────────── Bayon: carved sandstone ───────────────────────────

STONE_HI, STONE_LO, STONE_ABYSS, CARVED, LATERITE = '#d8cbad', '#665841', '#8e7f65', '#2f261a', '#9a3b22'
BAYON_LEVELS = ('#6d7c4e', '#b5862b', '#b0541f', '#8c2a1e')


@functools.lru_cache(maxsize=None)
def stone_base(count):
    rnd = random.Random(5)
    fine = Image.effect_noise((SIZE, SIZE), 30).filter(ImageFilter.GaussianBlur(.5))
    low = Image.effect_noise((16, 16), 40).resize((SIZE, SIZE), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(6))
    tone = ImageOps.autocontrast(Image.blend(fine, low, .3), cutoff=2)
    image = ImageOps.colorize(tone, black='#a1927a', mid='#b6a789', white='#c9bc9f').convert('RGBA')
    streaks = Image.new('RGBA', image.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(streaks)
    for _ in range(26):  # rain-weathering down the face of the wall
        x = rnd.randrange(SIZE)
        top = rnd.randrange(0, SIZE - 60)
        sd.line((x, top, x + rnd.choice((-1, 0, 1)), top + rnd.randrange(30, 120)), fill=(60, 48, 30, rnd.randrange(14, 30)))
    image.alpha_composite(streaks.filter(ImageFilter.GaussianBlur(.5)))
    carving = ImageDraw.Draw(image)
    for sl in slots(count, top=3, pitch=79, height=75):
        box = (6, sl.y + 2, 233, sl.y + sl.h - 3)
        floor = Image.new('RGBA', (box[2] - box[0], box[3] - box[1]), (70, 56, 36, 46))
        image.alpha_composite(floor, (box[0], box[1]))
        carving.line((box[0], box[1], box[2], box[1]), fill=STONE_LO, width=2)  # shadow under the upper lip
        carving.line((box[0], box[1], box[0], box[3]), fill=STONE_LO, width=2)
        carving.line((box[0] + 1, box[3], box[2], box[3]), fill=STONE_HI)  # light on the lower lip
        carving.line((box[2], box[1] + 1, box[2], box[3]), fill=STONE_HI)
        if sl.count <= 3:  # a frieze of lotus petals cut along the top of the panel
            for x in range(14, 224, 8):
                petal = [(x, box[1] + 9), (x + 4, box[1] + 4), (x + 8, box[1] + 9)]
                carving.line([(px + 1, py + 1) for px, py in petal], fill=STONE_HI)
                carving.line(petal, fill=STONE_LO)
    return image


def carve(cv, xy, text, font, fill=CARVED, anchor='la'):
    """Type cut into stone: a bright lip below and to the right of a dark cut."""
    cv.text((xy[0] + 1, xy[1] + 1), text, font, STONE_HI, anchor=anchor)
    cv.text(xy, text, font, fill, anchor=anchor)


def render_bayon(snapshot):
    cv = Canvas('#000000')
    cv.base.paste(stone_base(len(overview_rows(snapshot))), (0, 0))
    for sl, row, used, tag, old, reset in entries(snapshot):
        y, h = sl.y, sl.h
        top = y + (12 if sl.count <= 3 else 5)
        ch = y + h - 4 - top
        # a medallion with the provider's mark, and the name
        mark = max(10, round(13 * sl.small))
        mx, my = 16, round(top + ch * .08)
        cv.draw.ellipse((mx + 1, my + 1, mx + mark + 5, my + mark + 5), outline=STONE_HI)
        cv.draw.ellipse((mx, my, mx + mark + 4, my + mark + 4), outline=CARVED)
        cv.ink.alpha_composite(glyph(row['provider'], mark, CARVED), (mx + 2, my + 2))
        size = sl.txt(10)
        room = 226 - (mx + mark + 14) - (cv.draw.textlength(tag, font=latin(size, 800)) + 12 if tag else 0)
        mid = my + (mark + 4) / 2
        cv.spaced((mx + mark + 11, round(mid)), fit_text(cv.draw, account_label(row), latin(size, 800), room).upper(),
                  latin(size, 800), CARVED, 1.1, anchor='lm')
        if tag:
            cv.text((226, round(mid)), tag, latin(size, 800), LATERITE if old else '#4d4130', anchor='rm')
        # the number, cut deep, and the time left
        base = round(top + ch * .84) - (round(sl.k * 3) if sl.count > 1 else 0)
        nfont = face('noto-serif-khmer-700.woff2', min(sl.num(28), 46))
        if used is None:
            numeral(cv, 16, base, None, nfont, CARVED)
        else:
            text = khmer_number(used)
            carve(cv, (16, base), text, nfont, anchor='ls')
            right = 16 + cv.draw.textlength(text, font=nfont)
            carve(cv, (right + 3, base), '%', latin(sl.num(14), 800), LATERITE, anchor='ls')
        # the gauge: ten slots cut in the stone, filled with ground pigment
        gh = max(5, round(8 * min(sl.k, 1.5)))
        gy = y + h - 4 - gh - 3
        carve(cv, (226, base if sl.count > 1 else gy - 12), khmer_time(reset),
              face('battambang-700.woff2', min(sl.txt(17), 18)), anchor='rs')
        cell, gap = (210 - 9 * 3) / 10, 3
        for i in range(10):
            a = 16 + i * (cell + gap)
            box = (round(a), gy, round(a + cell) - 1, gy + gh - 1)
            cv.draw.rectangle(box, fill=STONE_ABYSS)
            cv.draw.line((box[0], box[1], box[2], box[1]), fill=STONE_LO)  # the cut's shadow
            cv.draw.line((box[0], box[3] + 1, box[2], box[3] + 1), fill=STONE_HI)
            if used is None:
                continue
            frac = max(0, min(1, used / 10 - i))
            if frac <= 0:
                continue
            fill = level_color(BAYON_LEVELS, used)
            fb = (box[0], box[1] + 1, max(box[0], round(a + cell * frac) - 1), box[3])
            cv.draw.rectangle(fb, fill=fill)
            cv.draw.line((fb[0], fb[1], fb[2], fb[1]), fill=mix(fill, '#ffffff', .22))
            if old:
                stale_hatch(cv.draw, fb, STONE_ABYSS)
    return cv.finish(blur=1)


# ───────────────────────── Sastra: palm-leaf manuscript ─────────────────────────

LACQUER, LEAF_A, LEAF_B, LEAF_INK, LEAF_LIGHT, CORD = '#1f150e', '#dac891', '#cdb67a', '#2a1c10', '#eddca8', '#a83b2a'
SASTRA_LEVELS = ('#2a1c10', '#6a4616', '#a4521b', '#9c2a1d')
HOLES = (19, 221)


@functools.lru_cache(maxsize=None)
def leaf_base(count):
    rnd = random.Random(9)
    base = rgb(LACQUER)
    image = Image.new('RGB', (SIZE, SIZE))
    px = image.load()
    grain = [rnd.randint(-4, 4) for _ in range(SIZE)]
    for y in range(SIZE):
        for x in range(SIZE):
            d = grain[x]
            px[x, y] = (max(0, base[0] + d), max(0, base[1] + d), max(0, base[2] + d))
    image = image.convert('RGBA')
    draw = ImageDraw.Draw(image)
    fibres = Image.new('RGBA', image.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fibres)
    for x in HOLES:  # the cord the leaves are strung on, seen between them
        draw.line((x, 0, x, SIZE), fill=CORD, width=3)
        draw.line((x - 1, 0, x - 1, SIZE), fill=mix(CORD, '#ffffff', .25))
    for sl in slots(count, top=3, pitch=79, height=75):
        x0, x1, y0, y1 = 5, 234, sl.y + 2, sl.y + sl.h - 3
        fibre = [rnd.randint(-3, 3) for _ in range(x1 - x0 + 1)]
        for x in range(x0, x1 + 1):
            colour = mix(LEAF_A, LEAF_B, (x - x0) / (x1 - x0))
            top = y0 + rnd.choice((0, 0, 1))  # a cut edge is never ruler-straight
            bottom = y1 - rnd.choice((0, 0, 1))
            shade = fibre[x - x0]
            draw.line((x, top, x, bottom), fill=tuple(max(0, min(255, c + shade)) for c in colour) + (255,))
        for _ in range(sl.h // 3):  # a few longer fibres that run the whole strip
            fx = rnd.randrange(x0 + 2, x1 - 2)
            fd.line((fx, y0 + 1, fx, y1 - 1), fill=(90, 66, 24, 34))
    image.alpha_composite(fibres)
    draw = ImageDraw.Draw(image)
    for sl in slots(count, top=3, pitch=79, height=75):
        y0, y1 = sl.y + 2, sl.y + sl.h - 3
        mid = (y0 + y1) // 2
        for x in HOLES:  # string holes, the cord running through each
            draw.ellipse((x - 5, mid - 5, x + 5, mid + 5), fill=LACQUER)
            draw.line((x, mid - 5, x, mid + 5), fill=CORD, width=3)
            draw.line((x - 1, mid - 5, x - 1, mid + 5), fill=mix(CORD, '#ffffff', .25))
    return image


def render_sastra(snapshot):
    cv = Canvas('#000000')
    cv.base.paste(leaf_base(len(overview_rows(snapshot))), (0, 0))

    def incise(xy, text, font, fill=LEAF_INK, anchor='la'):
        cv.text((xy[0] + 1, xy[1] + 1), text, font, LEAF_LIGHT, anchor=anchor)  # the leaf's bright cut edge
        cv.text(xy, text, font, fill, anchor=anchor)

    x0, x1 = 36, 204
    for sl, row, used, tag, old, reset in entries(snapshot):
        y, h = sl.y, sl.h
        size = sl.txt(9)
        room = x1 - x0 - 4 - (cv.draw.textlength(tag, font=latin(size, 800)) + 12 if tag else 0)
        ly = round(y + h * .2) + 1
        incise((x0, ly), fit_text(cv.draw, account_label(row), latin(size, 800), room).upper(), latin(size, 800), anchor='lm')
        if tag:
            incise((x1, ly), tag, latin(size, 800), SASTRA_LEVELS[2] if old else '#5b4528', anchor='rm')
        base = round(y + h * (.74 if sl.count == 4 else .70))
        nfont = face('bokor.woff2', min(round(sl.num(30) * (.8 if sl.count == 4 else 1)), 50))
        if used is None:
            numeral(cv, x0, base, None, nfont, LEAF_INK)
        else:
            text = khmer_number(used)
            incise((x0, base), text, nfont, anchor='ls')
            right = x0 + cv.draw.textlength(text, font=nfont)
            incise((right + 3, base), '%', latin(sl.num(13), 800), '#5b4528', anchor='ls')
        # the gauge: a ruled line with a tick at every ten per cent, ink laid along it as far as the reading
        gy = round(y + h * .87)
        incise((x1, base if sl.count > 1 else gy - 14), khmer_time(reset),
               face('battambang-700.woff2', min(sl.txt(15), 17)), anchor='rs')
        width = x1 - x0
        cv.draw.line((x0, gy, x1, gy), fill='#a58f55', width=1)
        for i in range(11):
            tx = round(x0 + width * i / 10)
            tall = 5 if i % 5 == 0 else 3
            cv.draw.line((tx, gy - tall, tx, gy + 1), fill='#8a7442')
        if used is None:
            for tx in range(x0, x1, 4):
                cv.draw.point((tx, gy - 1), fill='#8a7442')
            continue
        end = x0 + round(width * used / 100)
        bar = (x0, gy - 3, max(x0, end), gy + 1)
        cv.draw.rectangle(bar, fill=level_color(SASTRA_LEVELS, used))
        if old:
            stale_hatch(cv.draw, bar, LEAF_A, step=3)
    return cv.finish(blur=1)


# ───────────────────────── Kbach: gold ornament on lacquer ─────────────────────────

@functools.lru_cache(maxsize=None)
def kbach_base(count):
    image = kbach.lacquer().copy()
    draw = ImageDraw.Draw(image)
    for sl in slots(count, top=3, pitch=79, height=75):
        y0 = sl.y + sl.h - kbach.BAND - 1
        image.alpha_composite(kbach.vine(SIZE), (0, y0))
        draw.line((0, y0 - 1, SIZE, y0 - 1), fill=mix(kbach.GOLD_LO, kbach.LACQUER, .4))
    return image


def render_kbach(snapshot):
    cv = Canvas('#000000')
    cv.base.paste(kbach_base(len(overview_rows(snapshot))), (0, 0))
    for sl, row, used, tag, old, reset in entries(snapshot):
        y, ch = sl.y, sl.h - kbach.BAND - 1
        mark = max(10, round(12 * sl.small))
        my = round(y + ch * .17 - mark / 2 + 2)
        cv.ink.alpha_composite(glyph(row['provider'], mark, kbach.GOLD), (14, my))
        size = sl.txt(10)
        room = 226 - (30 + (cv.draw.textlength(tag, font=latin(size)) + 12 if tag else 0))
        cv.spaced((14 + mark + 6, round(y + ch * .17 + 2)),
                  fit_text(cv.draw, account_label(row), latin(size), room).upper(), latin(size), kbach.GOLD_TEXT, 1.2, anchor='lm')
        cv.spaced((226, round(y + ch * .17 + 2)), tag, latin(size), '#f08a55' if old else kbach.GOLD, 1.2, anchor='rm')
        base = round(y + ch * .74)
        nfont = face('moul.woff2', min(round(sl.num(26) * (.8 if sl.count == 4 else 1)), 42))
        if used is None:
            right = numeral(cv, 14, base, None, nfont, kbach.GOLD)
        else:
            text = khmer_number(used)
            kbach.gilded(cv, (14, base), text, nfont, anchor='ls')
            right = 14 + cv.draw.textlength(text, font=nfont)
            cv.text((right + 3, base), '%', latin(sl.num(14), 800), kbach.GOLD, anchor='ls')
        gh = max(5, round(7 * min(sl.k, 1.5)))
        gy = round(y + ch - gh - 2)
        cv.text((226, base if sl.count > 1 else gy - 12), khmer_time(reset),
                face('battambang-700.woff2', min(sl.txt(17), 18)), kbach.GOLD_TEXT, anchor='rs')
        cell, gap = (212 - 9 * 3) / 10, 3
        for i in range(10):  # ten gilt-edged cells; the pigment inside says how much is used
            a = 14 + i * (cell + gap)
            box = (round(a), gy, round(a + cell) - 1, gy + gh - 1)
            cv.draw.rectangle(box, fill='#12060a', outline=kbach.GOLD_LO)
            if used is None:
                continue
            frac = max(0, min(1, used / 10 - i))
            if frac <= 0:
                continue
            fill = level_color(kbach.LEVELS, used)
            fb = (box[0] + 1, box[1] + 1, max(box[0] + 1, round(a + cell * frac) - 2), box[3] - 1)
            cv.draw.rectangle(fb, fill=fill)
            cv.draw.line((fb[0], fb[1], fb[2], fb[1]), fill=mix(fill, '#ffffff', .3))
            if old:
                stale_hatch(cv.draw, fb, '#12060a')
    return cv.finish(blur=1)
