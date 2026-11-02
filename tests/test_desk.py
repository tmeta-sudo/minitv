import datetime
import io
import json
import os
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from PIL import Image

from token_tv import cli, desk

MOMENT = datetime.datetime(2026, 11, 2, 10, 51, tzinfo=datetime.timezone(datetime.timedelta(hours=7)))  # a Monday


def write(path, data):
    Path(path).write_text(json.dumps(data), encoding='utf-8')
    return path


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / 'desk.json'

    def test_defaults_and_relative_board_file(self):
        write(self.path, {'pages': [{'type': 'clock'}, {'type': 'board', 'file': 'board.json'}]})
        config = desk.load_config(self.path)
        self.assertEqual(config['seconds'], 60)
        self.assertIsNone(config['night'])
        self.assertEqual(config['pages'][1]['file'], str(Path(self.dir.name) / 'board.json'))
        self.assertEqual(config['pages'][1]['max_age_minutes'], 120)

    def test_mistakes_are_named(self):
        bad = [({'pages': []}, 'at least one page'),
               ({'pages': [{'type': 'weather'}]}, 'page 1'),
               ({'pages': [{'type': 'clock'}], 'seconds': 5}, 'seconds'),
               ({'pages': [{'type': 'clock'}], 'seconds': True}, 'seconds'),
               ({'pages': [{'type': 'countdown', 'date': 'soon'}]}, '2027-04-14'),
               ({'pages': [{'type': 'board'}]}, 'file'),
               ({'pages': [{'type': 'clock'}], 'night': {'from': '25:00', 'to': '06:00'}}, 'night.from'),
               ({'pages': [{'type': 'clock'}], 'timezone': 7}, 'timezone')]
        for data, word in bad:
            write(self.path, data)
            with self.assertRaises(ValueError, msg=data) as caught:
                desk.load_config(self.path)
            self.assertIn(word, str(caught.exception))
        with self.assertRaises(ValueError):
            desk.load_config(Path(self.dir.name) / 'missing.json')

    def test_night_window_wraps_midnight(self):
        night = {'from': 23 * 60, 'to': 6 * 60}
        at = lambda h, m=0: MOMENT.replace(hour=h, minute=m)
        self.assertTrue(desk.in_night(at(23), night))
        self.assertTrue(desk.in_night(at(2, 30), night))
        self.assertFalse(desk.in_night(at(6), night))
        self.assertFalse(desk.in_night(at(12), night))
        self.assertFalse(desk.in_night(at(12), None))
        self.assertTrue(desk.in_night(at(13), {'from': 12 * 60, 'to': 14 * 60}))
        self.assertFalse(desk.in_night(at(15), {'from': 12 * 60, 'to': 14 * 60}))
        self.assertFalse(desk.in_night(at(15), {'from': 600, 'to': 600}))

    def test_pages_take_turns_on_the_clock_of_the_epoch(self):
        self.assertEqual([desk.page_index(t, 60, 3) for t in (0, 59, 60, 120, 180)], [0, 0, 1, 2, 0])


class TextTest(unittest.TestCase):
    def test_runs_keep_each_script_in_its_own_font(self):
        kinds = [kind for kind, _ in desk.runs('Disk ថ្ងៃ')]
        self.assertEqual(kinds, [False, True])
        self.assertEqual(''.join(text for _, text in desk.runs('A ក B')), 'A ក B')

    def test_khmer_names(self):
        with mock.patch.object(desk, 'SHAPING', True):
            self.assertEqual(desk.names(MOMENT), ('ច័ន្ទ', 'វិច្ឆិកា'))
        with mock.patch.object(desk, 'SHAPING', False):
            self.assertEqual(desk.names(MOMENT), ('MON', 'NOV'))
        self.assertEqual(desk.khmer_digits(1024), '១០២៤')


class PagesTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.board = Path(self.dir.name) / 'board.json'

    def page(self, **extra):
        return {'type': 'board', 'file': str(self.board), 'max_age_minutes': 60, **extra}

    def test_every_page_is_a_240_jpeg_the_clock_accepts(self):
        write(self.board, desk.EXAMPLE_BOARD)
        pages = [{'type': 'clock'}, {'type': 'calendar'}, self.page(),
                 {'type': 'countdown', 'label': 'Khmer New Year', 'date': datetime.date(2027, 4, 14)}]
        for page in pages:
            data = desk.to_jpeg(desk.render_page(page, MOMENT, time.time()))
            self.assertLessEqual(len(data), desk.MAX_JPEG, page['type'])
            self.assertEqual(Image.open(io.BytesIO(data)).size, (240, 240))
        self.assertEqual(desk.to_jpeg(desk.render_night())[:2], b'\xff\xd8')

    def test_countdown_days(self):
        self.assertEqual(desk.days_until(datetime.date(2027, 4, 14), MOMENT), 163)
        self.assertEqual(desk.days_until(datetime.date(2026, 11, 2), MOMENT), 0)
        self.assertEqual(desk.days_until(datetime.date(2026, 11, 1), MOMENT), -1)
        for day in (datetime.date(2026, 11, 2), datetime.date(2026, 10, 1), datetime.date(2030, 1, 1)):
            self.assertEqual(desk.render_countdown(MOMENT, {'label': 'x', 'date': day}).size, (240, 240))

    def test_board_states_never_invent_a_row(self):
        now = time.time()
        title, items, state = desk.read_board(self.page(), now)  # no file
        self.assertEqual((items, state), ([], 'none'))
        self.board.write_text('not json', encoding='utf-8')
        self.assertEqual(desk.read_board(self.page(), now)[2], 'none')
        write(self.board, {'items': 'nope'})
        self.assertEqual(desk.read_board(self.page(), now)[2], 'none')
        write(self.board, {'title': 'T', 'items': [{'label': 'A', 'value': 3, 'percent': 250},
                                                    {'label': 'B', 'percent': -5}, {'value': 'no label'}, 'junk',
                                                    {'label': 'C', 'percent': True, 'value': {'a': 1}}]})
        title, items, state = desk.read_board(self.page(), now)
        self.assertEqual((title, state), ('T', 'ok'))
        self.assertEqual([i['label'] for i in items], ['A', 'B', 'C'])
        self.assertEqual([i['percent'] for i in items], [100, 0, None])  # clamped; a bool is no percent
        self.assertEqual([i['value'] for i in items], ['3', '', ''])
        self.assertEqual(desk.read_board(self.page(), now + 61 * 60)[2], 'old')

    def test_board_shows_at_most_five_rows(self):
        write(self.board, {'items': [{'label': str(i)} for i in range(9)]})
        self.assertEqual(len(desk.read_board(self.page(), time.time())[1]), desk.BOARD_ROWS)

    def test_missing_or_old_boards_look_different_from_fresh_ones(self):
        write(self.board, desk.EXAMPLE_BOARD)
        now = time.time()
        fresh = desk.render_board(MOMENT, self.page(), now).tobytes()
        old = desk.render_board(MOMENT, self.page(), now + 3 * 3600).tobytes()
        self.board.unlink()
        none = desk.render_board(MOMENT, self.page(), now).tobytes()
        self.assertEqual(len({fresh, old, none}), 3)


class Display:
    """A clock that records what it is told, and can be made to fail."""
    def __init__(self, fail=0):
        self.sent, self.selected, self.fail = [], [], fail

    def put(self, name, image, digest):
        if self.fail:
            self.fail -= 1
            raise OSError('no answer')
        self.sent.append((name, image, digest))
        return name, []

    def select(self, original, slot):
        self.selected.append((original, slot))


class Stop:
    """A stop signal that lets the loop turn `turns` times."""
    def __init__(self, turns):
        self.turns = turns

    def wait(self, seconds):
        self.turns -= 1
        return self.turns <= 0


class RunTest(unittest.TestCase):
    config = {'seconds': 60, 'night': None, 'timezone': None, 'device_url': None,
              'pages': [{'type': 'clock'}, {'type': 'calendar'}]}

    def run_desk(self, display, times, config=None, **options):
        clock = iter(times)
        said = []
        desk.run(config or self.config, display, {'saved': 1}, now=lambda: next(clock), stop=Stop(len(times) // 2),
                 say=lambda text, **_: said.append(text), **options)
        return said

    def test_sends_each_new_page_and_selects_it(self):
        display = Display()
        base = 1_800_000_000 // 60 * 60
        self.run_desk(display, [base, base, base + 60, base + 60])
        self.assertEqual(len(display.sent), 2)
        self.assertEqual({name for name, *_ in display.sent}, {'tokentv.jpg'})
        self.assertEqual(len(display.selected), 2)
        self.assertEqual(display.selected[0][0], {'saved': 1})

    def test_an_identical_picture_is_not_written_again(self):
        display = Display()
        night = dict(self.config, night={'from': 0, 'to': 24 * 60 - 1}, pages=[{'type': 'clock'}])
        base = 1_800_000_000 // 60 * 60
        self.run_desk(display, [base, base, base + 60, base + 60, base + 120, base + 120], night)
        self.assertEqual(len(display.sent), 1)

    def test_a_failed_send_is_tried_again_next_turn(self):
        display = Display(fail=1)
        base = 1_800_000_000 // 60 * 60
        said = self.run_desk(display, [base, base, base + 60, base + 60])
        self.assertEqual(len(display.sent), 1)
        self.assertIn('did not take', said[0])

    def test_once_sends_one_picture_and_stops(self):
        display = Display()
        clock = iter([1_800_000_000, 1_800_000_000])
        desk.run(self.config, display, {}, now=lambda: next(clock), once=True, say=lambda *a, **k: None)
        self.assertEqual(len(display.sent), 1)


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.config = str(Path(self.dir.name) / 'config.json')

    def call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(['desk', '--config', self.config, *argv])
        return code, out.getvalue(), err.getvalue()

    def test_init_writes_examples_and_never_overwrites(self):
        self.assertEqual(self.call('--init')[0], 0)
        desk_json = Path(self.dir.name) / 'desk.json'
        self.assertTrue(desk_json.is_file() and (Path(self.dir.name) / 'board.json').is_file())
        desk_json.write_text(json.dumps({'pages': [{'type': 'clock'}]}), encoding='utf-8')
        code, out, _ = self.call('--init')
        self.assertIn('left as it is', out)
        self.assertEqual(json.loads(desk_json.read_text(encoding='utf-8')), {'pages': [{'type': 'clock'}]})

    def test_out_draws_every_page_without_a_clock(self):
        self.call('--init')
        out_dir = Path(self.dir.name) / 'pages'
        code, text, _ = self.call('--out', str(out_dir))
        self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in out_dir.iterdir()),
                         ['desk-1-clock.jpg', 'desk-2-calendar.jpg', 'desk-3-countdown.jpg', 'desk-4-board.jpg', 'desk-night.jpg'])

    def test_no_config_and_no_clock_say_what_to_do(self):
        code, _, err = self.call()
        self.assertEqual(code, 1)
        self.assertIn('desk --init', err)
        self.call('--init')
        code, _, err = self.call()
        self.assertEqual(code, 1)
        self.assertIn('--device-url', err)


if __name__ == '__main__':
    unittest.main()
