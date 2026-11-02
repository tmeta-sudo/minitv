"""Desk mode: the same little screen, showing things that are not token usage.

    token-tv desk --init            write an example desk.json and board.json beside your config
    token-tv desk --out pages       draw every page to a folder, no clock needed
    token-tv desk                   rotate the pages on your clock

Pages (set in desk.json, in the order you list them):
    clock      the time in Khmer numerals, the weekday, day, month and year in Khmer
    calendar   this month, Sunday first, today marked
    countdown  days until a date you name, with your own label
    board      anything at all, from a JSON file that any script can write (see below)

A board file is {"title": "Studio", "items": [{"label": "Disk", "value": "72%", "percent": 72},
{"label": "Build", "value": "passing"}]}: a label, a value, and a gauge when `percent` is given. A board
older than `max_age_minutes` is marked OLD and a missing or unreadable one shows a dash and NO DATA; nothing
is invented. It talks to the clock through the same upload code TokenTV uses, so it keeps TokenTV's rules:
one program per clock, the clock's original photo settings saved first and restorable with --restore.
"""
import datetime
import functools
import hashlib
import io
import json
import re
import sys
import threading
import time
from http.client import HTTPException
from pathlib import Path

from PIL import Image, ImageDraw

from token_tv import kbach
from token_tv.khmer import DIGITS, SHAPING, latin
from token_tv.themes import SIZE, Canvas, face, mix

PAGE_TYPES = ('clock', 'calendar', 'countdown', 'board')
MIN_SECONDS, MAX_SECONDS = 30, 3600
MAX_JPEG = 58000  # the clock's album takes a JPEG up to 60 000 bytes
BOARD_ROWS = 5

WEEKDAYS = ('ច័ន្ទ', 'អង្គារ', 'ពុធ', 'ព្រហស្បតិ៍', 'សុក្រ', 'សៅរ៍', 'អាទិត្យ')  # Monday first, as Python counts
WEEKDAYS_SHORT = ('ច', 'អ', 'ពុ', 'ព្រ', 'សុ', 'ស', 'អា')
MONTHS = ('មករា', 'កុម្ភៈ', 'មីនា', 'មេសា', 'ឧសភា', 'មិថុនា', 'កក្កដា', 'សីហា', 'កញ្ញា', 'តុលា', 'វិច្ឆិកា', 'ធ្នូ')
DAY_WORD, TODAY_WORD = 'ថ្ងៃ', 'ថ្ងៃនេះ'
LATIN_WEEKDAYS = ('MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN')
LATIN_MONTHS = ('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC')

EXAMPLE = {
    'timezone': 'Asia/Phnom_Penh',
    'seconds': 60,
    'night': {'from': '23:00', 'to': '06:00'},
    'pages': [
        {'type': 'clock'},
        {'type': 'calendar'},
        {'type': 'countdown', 'label': 'Khmer New Year', 'date': '2027-04-14'},
        {'type': 'board', 'file': 'board.json', 'max_age_minutes': 120},
    ],
}
EXAMPLE_BOARD = {'title': 'Studio', 'items': [
    {'label': 'Disk', 'value': '72%', 'percent': 72},
    {'label': 'Backup', 'value': 'last night'},
    {'label': 'Build', 'value': 'passing'},
]}


# ───────────────────────────── config ─────────────────────────────

def parse_clock(text, where):
    match = re.fullmatch(r'([01]?\d|2[0-3]):([0-5]\d)', text) if isinstance(text, str) else None
    if not match:
        raise ValueError(f'{where} must look like "23:00"')
    return int(match.group(1)) * 60 + int(match.group(2))


def load_config(path):
    """The desk config at `path`, checked: a dict with defaults filled in. Raises ValueError saying what is wrong."""
    path = Path(path).expanduser()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except OSError as error:
        raise ValueError(f'Cannot read {path} ({error.strerror or error}). Make one with: token-tv desk --init') from None
    except ValueError as error:
        raise ValueError(f'{path} is not valid JSON ({error})') from None
    if not isinstance(data, dict):
        raise ValueError(f'{path} must hold one JSON object')
    seconds = data.get('seconds', 60)
    if isinstance(seconds, bool) or not isinstance(seconds, int) or not MIN_SECONDS <= seconds <= MAX_SECONDS:
        raise ValueError(f'"seconds" must be a whole number from {MIN_SECONDS} to {MAX_SECONDS}: it is how long each page '
                         'stays, and every change is written to the clock\'s memory')
    pages = data.get('pages')
    if not isinstance(pages, list) or not pages:
        raise ValueError('"pages" must be a list with at least one page')
    clean = []
    for i, page in enumerate(pages, 1):
        if not isinstance(page, dict) or page.get('type') not in PAGE_TYPES:
            raise ValueError(f'page {i}: "type" must be one of {", ".join(PAGE_TYPES)}')
        page = dict(page)
        if page['type'] == 'countdown':
            try:
                page['date'] = datetime.date.fromisoformat(str(page.get('date')))
            except ValueError:
                raise ValueError(f'page {i}: "date" must look like 2027-04-14') from None
            if not isinstance(page.get('label', ''), str):
                raise ValueError(f'page {i}: "label" must be text')
            page['label'] = page.get('label', '')[:40]
        if page['type'] == 'board':
            if not isinstance(page.get('file'), str) or not page['file']:
                raise ValueError(f'page {i}: "file" names the JSON file the board shows')
            age = page.get('max_age_minutes', 120)
            if isinstance(age, bool) or not isinstance(age, (int, float)) or age <= 0:
                raise ValueError(f'page {i}: "max_age_minutes" must be a positive number')
            page['file'] = str((path.parent / page['file']).expanduser()) if not Path(page['file']).is_absolute() else page['file']
            page['max_age_minutes'] = age
        clean.append(page)
    night = data.get('night')
    if night is not None:
        if not isinstance(night, dict):
            raise ValueError('"night" must look like {"from": "23:00", "to": "06:00"}')
        night = {'from': parse_clock(night.get('from'), '"night.from"'), 'to': parse_clock(night.get('to'), '"night.to"')}
    zone = data.get('timezone')
    if zone is not None and not isinstance(zone, str):
        raise ValueError('"timezone" must be a name such as "Asia/Phnom_Penh"')
    url = data.get('device_url')
    if url is not None and not isinstance(url, str):
        raise ValueError('"device_url" must be the clock address, such as "http://192.168.0.50"')
    return {'seconds': seconds, 'pages': clean, 'night': night, 'timezone': zone, 'device_url': url}


def timezone_of(name):
    """The configured time zone, or this computer's own (with a note) when it cannot be found."""
    if name:
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo(name), None
        except Exception:
            return None, f'Time zone {name!r} is unknown on this computer (Windows needs the tzdata package); using local time.'
    return None, None


def moment_at(epoch, zone=None):
    return datetime.datetime.fromtimestamp(epoch, zone) if zone else datetime.datetime.fromtimestamp(epoch).astimezone()


def in_night(moment, night):
    if not night:
        return False
    now = moment.hour * 60 + moment.minute
    start, end = night['from'], night['to']
    if start == end:
        return False
    return start <= now < end if start < end else now >= start or now < end


def page_index(epoch, seconds, count):
    """Which page shows now: the pages take turns of `seconds`, counted from the epoch, so a restart picks up in step."""
    return int(epoch // seconds) % count


# ───────────────────────────── drawing helpers ─────────────────────────────

def khmer_digits(value):
    return str(value).translate(DIGITS)


def is_khmer(ch):
    return 'ក' <= ch <= '៿' or '᧠' <= ch <= '᧿'


def runs(text):
    """Split text into (khmer?, run): Khmer script in the Khmer font, everything else in Latin; spaces and
    punctuation stay with the run before them."""
    out = []
    for ch in text:
        kind = is_khmer(ch) if not (ch.isspace() or ch in '.,:;-–—/()%+!?\'"') or not out else out[-1][0]
        if out and out[-1][0] == kind:
            out[-1][1] += ch
        else:
            out.append([kind, ch])
    return [(k, t) for k, t in out]


def font_for(khmer, size):
    return face('battambang-700.woff2', size) if khmer else latin(size, 700)


def width_of(draw, text, size):
    return sum(draw.textlength(t, font=font_for(k, size)) for k, t in runs(text))


def mixed(cv, xy, text, size, fill, anchor='ms', gild=False):
    """Text in a mix of Khmer and Latin, each in a font that has its letters. `anchor` is l/m/r then 's' (baseline)."""
    x, y = xy
    total = width_of(cv.draw, text, size)
    x -= total if anchor[0] == 'r' else total / 2 if anchor[0] == 'm' else 0
    for khmer, part in runs(text):
        font = font_for(khmer, size)
        if gild:
            kbach.gilded(cv, (round(x), y), part, font, anchor='ls')
        else:
            cv.text((round(x), y), part, font, fill, anchor='ls')
        x += cv.draw.textlength(part, font=font)


def fit_mixed(draw, text, size, room):
    if width_of(draw, text, size) <= room:
        return text
    while text and width_of(draw, text + '..', size) > room:
        text = text[:-1]
    return text.rstrip() + '..'


@functools.lru_cache(maxsize=None)
def frame_base():
    image = kbach.lacquer().copy()
    image.alpha_composite(kbach.vine(SIZE, flip=True), (0, 3))
    image.alpha_composite(kbach.vine(SIZE), (0, SIZE - kbach.BAND - 3))
    return image


def canvas():
    cv = Canvas('#000000')
    cv.base.paste(frame_base(), (0, 0))
    return cv


def diamond(draw, cx, cy, r, fill):
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def names(moment):
    """Weekday, month and day-word in Khmer, or in Latin where this computer cannot shape Khmer script."""
    if SHAPING:
        return WEEKDAYS[moment.weekday()], MONTHS[moment.month - 1]
    return LATIN_WEEKDAYS[moment.weekday()], LATIN_MONTHS[moment.month - 1]


# ───────────────────────────── pages ─────────────────────────────

def render_clock(moment):
    cv = canvas()
    weekday, month = names(moment)
    mixed(cv, (120, 66), (DAY_WORD if SHAPING else '') + weekday, 24, kbach.GOLD_TEXT)
    hh, mm = khmer_digits(f'{moment.hour:02d}'), khmer_digits(f'{moment.minute:02d}')
    size = 62
    while size > 30:
        font = face('moul.woff2', size)
        gap = size * .32
        total = cv.draw.textlength(hh, font=font) + gap + cv.draw.textlength(mm, font=font)
        if total <= 212:
            break
        size -= 2
    x = (SIZE - total) / 2
    base = 148
    kbach.gilded(cv, (round(x), base), hh, font, anchor='ls')
    cx = x + cv.draw.textlength(hh, font=font) + gap / 2
    for dy in (-size * .52, -size * .2):  # the colon: two small lozenges
        diamond(cv.draw, round(cx), round(base + dy), max(3, round(size * .06)), kbach.GOLD)
    kbach.gilded(cv, (round(x + cv.draw.textlength(hh, font=font) + gap), base), mm, font, anchor='ls')
    kbach.rule(cv.draw, 166, 50, 190)
    mixed(cv, (120, 200), f'{khmer_digits(moment.day)} {month} {khmer_digits(moment.year)}', 24, kbach.GOLD_TEXT)
    return cv.finish(blur=1)


def render_calendar(moment):
    import calendar as cal
    cv = canvas()
    _, month = names(moment)
    mixed(cv, (120, 44), f'{month} {khmer_digits(moment.year)}', 22, kbach.GOLD_TEXT)
    kbach.rule(cv.draw, 52, 24, 216)
    heads = WEEKDAYS_SHORT if SHAPING else ('S', 'M', 'T', 'W', 'T', 'F', 'S')
    order = (6, 0, 1, 2, 3, 4, 5) if SHAPING else (0, 1, 2, 3, 4, 5, 6)  # Sunday first
    for col, index in enumerate(order):
        label = heads[index] if SHAPING else heads[col]  # Latin letters are already in Sunday-first order
        mixed(cv, (21 + col * 33, 70), label, 13, kbach.GOLD)
    weeks = cal.Calendar(firstweekday=6).monthdayscalendar(moment.year, moment.month)
    for row, week in enumerate(weeks):
        for col, day in enumerate(week):
            if not day:
                continue
            cx, cy = 21 + col * 33, 88 + row * 22
            if day == moment.day:
                diamond(cv.draw, cx, cy - 1, 11, kbach.GOLD)
                mixed(cv, (cx, cy + 6), khmer_digits(day), 15, kbach.LACQUER)
            else:
                mixed(cv, (cx, cy + 6), khmer_digits(day), 15, kbach.GOLD_TEXT)
    return cv.finish(blur=1)


def days_until(target, moment):
    return (target - moment.date()).days


def render_countdown(moment, page):
    cv = canvas()
    label = page.get('label') or ''
    if label:
        mixed(cv, (120, 62), fit_mixed(cv.draw, label, 20, 200), 20, kbach.GOLD_TEXT)
    left = days_until(page['date'], moment)
    if left < 0:
        kbach.gilded(cv, (120 - cv.draw.textlength('--', font=latin(60)) / 2, 150), '--', latin(60, 800), anchor='ls')
        mixed(cv, (120, 196), 'PAST', 18, kbach.GOLD)
    elif left == 0 and SHAPING:
        mixed(cv, (120, 150), TODAY_WORD, 44, kbach.GOLD, gild=True)
    else:
        text = khmer_digits(left)
        size = 78
        while size > 36 and cv.draw.textlength(text, font=face('moul.woff2', size)) > 200:
            size -= 4
        font = face('moul.woff2', size)
        kbach.gilded(cv, ((SIZE - cv.draw.textlength(text, font=font)) / 2, 150), text, font, anchor='ls')
        mixed(cv, (120, 196), DAY_WORD if SHAPING else 'DAYS', 26, kbach.GOLD_TEXT)
    return cv.finish(blur=1)


def read_board(page, now):
    """(title, items, state) for a board page; state is 'ok', 'old' or 'none'. Never makes up a row."""
    path = Path(page['file'])
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
        age_minutes = (now - path.stat().st_mtime) / 60
    except (OSError, ValueError):
        return '', [], 'none'
    if not isinstance(raw, dict) or not isinstance(raw.get('items'), list):
        return '', [], 'none'
    items = []
    for item in raw['items'][:BOARD_ROWS]:
        if not isinstance(item, dict) or not isinstance(item.get('label'), str):
            continue
        percent = item.get('percent')
        if isinstance(percent, bool) or not isinstance(percent, (int, float)):
            percent = None
        value = item.get('value')
        value = str(value)[:24] if value is not None and not isinstance(value, (dict, list)) else ''
        items.append({'label': item['label'][:40], 'value': value,
                      'percent': None if percent is None else max(0, min(100, percent))})
    title = raw.get('title') if isinstance(raw.get('title'), str) else ''
    return title[:40], items, ('old' if age_minutes > page['max_age_minutes'] else 'ok') if items else 'none'


def render_board(moment, page, now):
    cv = canvas()
    title, items, state = read_board(page, now)
    if title:
        mixed(cv, (120, 44), fit_mixed(cv.draw, title, 20, 170), 20, kbach.GOLD_TEXT)
    if state != 'ok':
        tag = 'OLD' if state == 'old' else 'NO DATA'
        cv.spaced((226, 38), tag, latin(9, 800), '#f08a55', 1.2, anchor='rm')
    kbach.rule(cv.draw, 52, 24, 216)
    if not items:
        kbach.gilded(cv, (120 - cv.draw.textlength('--', font=latin(48)) / 2, 140), '--', latin(48, 800), anchor='ls')
        return cv.finish(blur=1)
    pitch = 33
    for i, item in enumerate(items):
        base = 80 + i * pitch
        value_w = width_of(cv.draw, item['value'], 15) if item['value'] else 0
        mixed(cv, (22, base), fit_mixed(cv.draw, item['label'], 14, 196 - value_w - 10), 14, kbach.GOLD_TEXT, anchor='ls')
        if item['value']:
            mixed(cv, (218, base), item['value'], 15, kbach.GOLD_HI if state == 'ok' else '#c9b78a', anchor='rs')
        if item['percent'] is not None:
            top = base + 6
            cv.draw.rectangle((22, top, 217, top + 4), fill='#12060a', outline=kbach.GOLD_LO)
            end = 23 + round(193 * item['percent'] / 100)
            if item['percent'] > 0:
                level = kbach.LEVELS[0 if item['percent'] < 50 else 1 if item['percent'] < 80 else 2 if item['percent'] < 90 else 3]
                cv.draw.rectangle((23, top + 1, max(23, end), top + 3), fill=level)
                if state == 'old':
                    for k in range(23, max(24, end), 4):
                        cv.draw.line((k, top + 3, k + 2, top + 1), fill='#12060a')
        else:
            cv.draw.line((22, base + 8, 217, base + 8), fill=mix(kbach.GOLD_LO, kbach.LACQUER, .5))
    return cv.finish(blur=1)


def render_night():
    """The night page: the lacquer left almost dark, so the screen is not a lamp in the room."""
    image = Image.new('RGB', (SIZE, SIZE), '#050202')
    layer = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    layer.alpha_composite(kbach.vine(SIZE), (0, SIZE // 2 - kbach.BAND // 2))
    faded = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    faded.paste(layer, (0, 0), layer.getchannel('A').point(lambda v: v * .28))
    image.paste(faded, (0, 0), faded)
    return image


def render_page(page, moment, now=None):
    now = time.time() if now is None else now
    kind = page['type']
    if kind == 'clock':
        return render_clock(moment)
    if kind == 'calendar':
        return render_calendar(moment)
    if kind == 'countdown':
        return render_countdown(moment, page)
    return render_board(moment, page, now)


def to_jpeg(image):
    """A JPEG the clock will take: under its 60 000 byte limit, lowering the quality only as far as it needs."""
    for quality in (92, 88, 84, 80, 74, 68):
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=quality, subsampling=0 if quality >= 88 else 2)
        if buffer.tell() <= MAX_JPEG:
            return buffer.getvalue()
    raise ValueError('The page does not fit the clock\'s 60 000 byte limit')


def frame(desk, epoch, zone=None):
    """(JPEG bytes, what it shows) for the moment `epoch`."""
    moment = moment_at(epoch, zone)
    if in_night(moment, desk['night']):
        return to_jpeg(render_night()), 'night'
    page = desk['pages'][page_index(epoch, desk['seconds'], len(desk['pages']))]
    return to_jpeg(render_page(page, moment, epoch)), page['type']


# ───────────────────────────── running ─────────────────────────────

def run(desk, display, original, *, zone=None, now=time.time, stop=None, once=False, say=print):
    """Draw the page for now, send it if it changed, wait for the next turn; until `stop` is set (or once)."""
    from token_tv.device import FILES
    stop = stop or threading.Event()
    last = None
    while True:
        epoch = now()
        try:
            image, shown = frame(desk, epoch, zone)
            digest = hashlib.sha256(image).hexdigest()
            if digest != last:  # an identical picture is not written to the clock's memory again
                slot, _ = display.put(FILES[0], image, digest)
                display.select(original, slot)
                last = digest
                say(f'{time.strftime("%H:%M:%S", time.localtime(epoch))}  {shown}', flush=True)
        except (OSError, ValueError, KeyError, HTTPException) as error:
            last = None  # what the clock shows is unknown now: the next picture goes in full
            say(f'The clock did not take the picture ({error}); trying again next turn.', flush=True)
        if once or stop.wait(max(1.0, desk['seconds'] - (now() % desk['seconds']))):
            return


def write_new(path, data):
    path = Path(path)
    if path.exists():
        print(f'{path} exists; left as it is.')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {path}')


def main(args):
    """`token-tv desk`: args carries config, desk_config, device_url, out, once, restore, init."""
    base = Path(args.config).expanduser().parent
    desk_path = Path(args.desk_config).expanduser() if args.desk_config else base / 'desk.json'
    if args.init:
        write_new(desk_path, EXAMPLE)
        write_new(desk_path.parent / 'board.json', EXAMPLE_BOARD)
        print(f'Try it without a clock: token-tv desk --out pages    then open the pictures in pages/')
        return 0
    try:
        desk = load_config(desk_path)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    zone, note = timezone_of(desk['timezone'])
    if note:
        print(note, file=sys.stderr)
    if args.out:
        out = Path(args.out).expanduser()
        out.mkdir(parents=True, exist_ok=True)
        epoch = time.time()
        moment = moment_at(epoch, zone)
        for i, page in enumerate(desk['pages'], 1):
            target = out / f'desk-{i}-{page["type"]}.jpg'
            target.write_bytes(to_jpeg(render_page(page, moment, epoch)))
            print(target)
        if desk['night']:
            (out / 'desk-night.jpg').write_bytes(to_jpeg(render_night()))
            print(out / 'desk-night.jpg')
        return 0
    url = args.device_url or desk['device_url']
    if not url:
        try:
            url = json.loads((base / 'config.json').read_text(encoding='utf-8')).get('device_url')
        except (OSError, ValueError, AttributeError):
            url = None
    if not url:
        print('No clock address. Pass --device-url 192.168.0.50 or put "device_url" in desk.json.', file=sys.stderr)
        return 1
    from token_tv.device import BackupMismatch, open_display
    from token_tv.live import hold_clock, hold_lock, load_original, mismatch_message, plain
    url = plain(url if '://' in url else 'http://' + url)
    state = base / 'state'
    backup = state / 'display-original.json'  # the same saved original `token-tv run` uses
    try:
        display = open_display(url)
    except ValueError as error:
        print(f'Cannot use the clock address {url!r}: {error}', file=sys.stderr)
        return 1
    if args.restore:
        if not backup.is_file():
            print('Nothing to restore: no saved original display settings.', file=sys.stderr)
            return 1
        original = json.loads(backup.read_text(encoding='utf-8'))
        try:
            display.check_backup(original)
        except BackupMismatch as error:
            print(mismatch_message(error, backup), file=sys.stderr)
            return 1
        display.restore(original)
        print('Original display selection restored.')
        return 0
    try:
        if not hold_lock(state, 'desk.lock'):
            print('Desk mode already runs with this config on this computer.', file=sys.stderr)
            return 1
    except OSError as error:
        print(f'Cannot write the state folder {state} ({error.strerror or error}).', file=sys.stderr)
        return 1
    if not hold_clock(url):
        print(f'Another TokenTV already drives the clock at {url}. One clock takes one program: stop that one first '
              '(token-tv autostart off, or end its terminal), then run this again.', file=sys.stderr)
        return 1
    try:
        original = load_original(display, backup)
    except (OSError, ValueError, HTTPException) as error:
        print(f'Could not read the clock at {url} ({error}). Is it on and on this network?', file=sys.stderr)
        return 1
    print(f'Desk mode: {len(desk["pages"])} page(s), a new one every {desk["seconds"]} s, on the clock at {url}. '
          'Ctrl+C stops it; `token-tv desk --restore` puts your clock\'s own display back.', flush=True)
    stop = threading.Event()
    try:
        run(desk, display, original, zone=zone, stop=stop, once=args.once)
    except KeyboardInterrupt:
        stop.set()
    return 0
