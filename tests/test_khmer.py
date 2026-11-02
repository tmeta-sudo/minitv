import io
import time
import unittest
from unittest import mock

from PIL import Image

from token_tv import khmer
from token_tv.display import STYLES, render_page
from token_tv.sample import D, H, SAMPLE, snapshot

FACES = ('hol', 'bayon', 'sastra', 'kbach')


class KhmerFacesTest(unittest.TestCase):
    def test_registered_and_rendered_as_240_jpegs(self):
        for name in FACES:
            self.assertIn(name, STYLES)
            image = Image.open(io.BytesIO(render_page(snapshot(time.time()), style=name)))
            self.assertEqual(image.size, (240, 240), name)

    def test_numerals_keep_the_value(self):
        self.assertEqual(khmer.khmer_number(72), '៧២')
        self.assertEqual(khmer.khmer_number(0), '០')
        self.assertEqual(khmer.khmer_number(100), '១០០')

    def test_unknown_is_a_dash_never_zero(self):
        self.assertEqual(khmer.khmer_number(None), '--')

    def test_time_in_khmer_words(self):
        with mock.patch.object(khmer, 'SHAPING', True):
            self.assertEqual(khmer.khmer_time('2d 6h'), '២ថ្ងៃ ៦ម៉ោង')
            self.assertEqual(khmer.khmer_time('3h 41m'), '៣ម៉ោង ៤១នាទី')
            self.assertEqual(khmer.khmer_time('4d 0h'), '៤ថ្ងៃ')  # a zero unit adds nothing
            self.assertEqual(khmer.khmer_time('0h 0m'), '០ម៉ោង')
            self.assertEqual(khmer.khmer_time('--'), '--')

    def test_latin_time_when_khmer_cannot_be_shaped(self):
        with mock.patch.object(khmer, 'SHAPING', False):
            self.assertEqual(khmer.khmer_time('2d 6h'), '2d 6h')

    def test_every_row_count_old_and_missing_readings(self):
        now = time.time()
        for name in FACES:
            render = getattr(khmer, 'render_' + name)
            for count in (1, 2, 3, 4):
                self.assertEqual(render(snapshot(now, SAMPLE[:count])).size, (240, 240), (name, count))
            data = snapshot(now, [('claude_a', 'CLAUDE A', 'claude', [('5H', 40, 2 * H)]),
                                  ('codex_a', 'CODEX A', 'codex', [('WEEK', 15, 4 * D)]),
                                  ('grok_a', 'GROK A', 'grok', [])])
            data['accounts']['codex_a']['status'] = 'stale'
            self.assertEqual(render(data).size, (240, 240), name)

    def test_a_reading_and_no_reading_look_different(self):
        now = time.time()
        known = snapshot(now, [('grok_a', 'GROK A', 'grok', [('BUDGET', 0, 3 * D)])])
        unknown = snapshot(now, [('grok_a', 'GROK A', 'grok', [])])
        for name in FACES:
            render = getattr(khmer, 'render_' + name)
            self.assertNotEqual(render(known).tobytes(), render(unknown).tobytes(), name)


if __name__ == '__main__':
    unittest.main()
