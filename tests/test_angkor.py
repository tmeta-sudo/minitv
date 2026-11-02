import io
import time
import unittest

from PIL import Image

from token_tv.angkor import khmer_number, render_angkor
from token_tv.display import STYLES, render_page
from token_tv.sample import D, H, SAMPLE, snapshot


class AngkorTest(unittest.TestCase):
    def test_registered_and_renders_a_240_jpeg(self):
        self.assertIn('angkor', STYLES)
        image = Image.open(io.BytesIO(render_page(snapshot(time.time()), style='angkor')))
        self.assertEqual(image.size, (240, 240))

    def test_khmer_numerals_keep_the_value(self):
        self.assertEqual(khmer_number(72), '៧២')
        self.assertEqual(khmer_number(0), '០')
        self.assertEqual(khmer_number(100), '១០០')

    def test_unknown_is_a_dash_never_zero(self):
        self.assertNotIn('០', khmer_number(None))
        self.assertEqual(khmer_number(None), '--')

    def test_one_to_four_rows_and_old_readings_render(self):
        now = time.time()
        for count in (1, 2, 3, 4):
            self.assertEqual(render_angkor(snapshot(now, SAMPLE[:count])).size, (240, 240))
        data = snapshot(now, [('claude_a', 'CLAUDE A', 'claude', [('5H', 40, 2 * H)]),
                              ('codex_a', 'CODEX A', 'codex', [('WEEK', 15, 4 * D)]),
                              ('grok_a', 'GROK A', 'grok', [])])
        data['accounts']['codex_a']['status'] = 'stale'
        self.assertEqual(render_angkor(data).size, (240, 240))


if __name__ == '__main__':
    unittest.main()
