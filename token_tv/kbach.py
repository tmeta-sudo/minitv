"""Kbach: Khmer ornament in gold on lacquer, shared by the `kbach` clock face and the desk pages.

*Kbach* is the Khmer word for the carved and painted ornament of temples, silverwork and dance costume:
vines that spring from a stem and curl into spirals, tipped with flame-shaped leaves. The band here is
drawn from that grammar (a waving stem, alternating curls above and below it, a leaf at each crossing)
at 4× and reduced, so the curls stay clean at 12 px.
"""
import functools
import math
import random

from PIL import Image, ImageDraw, ImageFilter

from token_tv.themes import SIZE, face, mix, rgb

LACQUER, LACQUER_HI = '#1c0a09', '#2b100d'
GOLD, GOLD_HI, GOLD_LO, GOLD_TEXT = '#d9a93a', '#f4d77e', '#7d5a1c', '#ecd9a0'
LEVELS = ('#6fae8a', '#e0b13e', '#e0662a', '#d8323a')  # jade, gold, vermilion, crimson: how much is used
BAND = 12  # height of the vine band in pixels
UNIT = 40  # width of one repeat


def spiral(cx, cy, r0, start, turns, direction, steps=48):
    """An Archimedean-style curl that winds in from radius r0 around (cx, cy)."""
    points = []
    for i in range(steps + 1):
        t = i / steps
        angle = start + direction * t * turns * 2 * math.pi
        r = r0 * (1 - t) ** .85 + .2
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return points


def leaf(draw, x, y, length, width, angle, fill):
    """A flame-shaped leaf: pointed at both ends, fullest a third along, laid along `angle`."""
    points = []
    for i in range(0, 21):
        t = i / 20
        w = width * math.sin(math.pi * t) * (1.25 - .5 * t)
        points.append((t * length, -w))
    for i in range(20, -1, -1):
        t = i / 20
        w = width * math.sin(math.pi * t) * (1.25 - .5 * t)
        points.append((t * length, w))
    c, s = math.cos(angle), math.sin(angle)
    draw.polygon([(x + px * c - py * s, y + px * s + py * c) for px, py in points], fill=fill)


@functools.lru_cache(maxsize=None)
def vine(width, height=BAND, flip=False):
    """A horizontal band of kbach vine, `width` × `height`, gold on a transparent ground."""
    s = 4
    image = Image.new('RGBA', (width * s, height * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    mid, amp = height * s / 2, height * s * .17
    unit = UNIT * s
    line = max(2, round(s * .95))

    def stem(x):
        return mid + amp * math.sin(2 * math.pi * x / unit)

    shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for layer, colour, dy in ((sd, GOLD_LO, s * .7), (draw, GOLD, 0)):
        layer.line([(x, stem(x) + dy) for x in range(0, width * s, 2)], fill=colour, width=line, joint='curve')
        for k in range(-1, width // UNIT + 2):
            base = k * unit
            # a curl above the stem at the crest, winding forward; one below at the trough, winding back
            px = base + unit * .25
            r = height * s * .3
            layer.line([(x, y + dy) for x, y in spiral(px + r * .15, stem(px) - r, r, math.pi / 2, 1.55, -1)],
                       fill=colour, width=line, joint='curve')
            qx = base + unit * .75
            layer.line([(x, y + dy) for x, y in spiral(qx - r * .15, stem(qx) + r, r, -math.pi / 2, 1.55, -1)],
                       fill=colour, width=line, joint='curve')
            for ax, ay, rr in ((px + r * .15, stem(px) - r, r * .22), (qx - r * .15, stem(qx) + r, r * .22)):
                layer.ellipse((ax - rr, ay - rr + dy, ax + rr, ay + rr + dy), fill=colour)  # the bead at each curl's heart
            leaf(layer, base + unit * .5 - height * s * .25, stem(base + unit * .5) + dy, height * s * .5, height * s * .11,
                 0.0, colour)
            leaf(layer, base - height * s * .25, stem(base) + dy, height * s * .5, height * s * .11, 0.0, colour)
    out = Image.new('RGBA', image.size, (0, 0, 0, 0))
    out.alpha_composite(shadow)
    out.alpha_composite(image)
    out = out.resize((width, height), Image.Resampling.LANCZOS)
    return out.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if flip else out


@functools.lru_cache(maxsize=None)
def lacquer(seed=21):
    """A lacquered panel: deep oxblood with a soft vertical sheen and a fine, even grain."""
    rnd = random.Random(seed)
    top, bottom = rgb(LACQUER_HI), rgb(LACQUER)
    image = Image.new('RGB', (SIZE, SIZE))
    px = image.load()
    for y in range(SIZE):
        t = abs(y - SIZE * .35) / SIZE
        base = tuple(round(top[i] + (bottom[i] - top[i]) * min(1, t * 1.6)) for i in range(3))
        for x in range(SIZE):
            n = rnd.randint(-2, 2)
            px[x, y] = (max(0, base[0] + n), max(0, base[1] + n), max(0, base[2] + n))
    return image.convert('RGBA')


def rule(draw, y, x0=0, x1=SIZE):
    """A thin gilt rule with a darker line beneath it."""
    draw.line((x0, y, x1, y), fill=GOLD)
    draw.line((x0, y + 1, x1, y + 1), fill=GOLD_LO)


def gilded(cv, xy, text, font, anchor='la', top=GOLD_HI, bottom=GOLD):
    """Text in gold leaf: a vertical gradient poured into the letters, with a dark edge below."""
    mask = Image.new('L', (SIZE, SIZE), 0)
    md = ImageDraw.Draw(mask)
    md.text(xy, text, font=font, fill=255, anchor=anchor)
    bbox = mask.getbbox()
    if not bbox:
        return
    shadow = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    shadow.paste(Image.new('RGBA', (SIZE, SIZE), GOLD_LO), (0, 1), mask)
    cv.ink.alpha_composite(shadow)
    ramp = Image.new('RGBA', (SIZE, SIZE))
    rd = ImageDraw.Draw(ramp)
    for y in range(bbox[1], bbox[3] + 1):
        rd.line((0, y, SIZE, y), fill=mix(top, bottom, (y - bbox[1]) / max(1, bbox[3] - bbox[1])) + (255,))
    cv.ink.paste(ramp, (0, 0), mask)
