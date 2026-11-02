# minitv: TokenTV, plus Khmer faces and a desk mode

A copy of [TokenTV](https://github.com/click6067-ship-it/token-tv) (MIT, see [LICENSE](LICENSE) and [NOTICE](NOTICE)) for a GeekMagic SmallTV, with two additions made from Cambodian craft rather than from pictures of it.

## 1. Four Khmer clock faces for token usage

<p align="center"><img src="docs/images/khmer-faces.png" width="800" alt="Hol, Bayon, Sastra and Kbach on sample data"></p>

| Face | Made from | Details |
| --- | --- | --- |
| `hol` | a silk *sampot hol* | woven indigo ground, ikat bands in natural dyes with feathered edges, gauges as woven blocks |
| `bayon` | carved sandstone | grained stone wall, recessed panels with a lotus-petal frieze, engraved type, slot gauges inlaid with pigment |
| `sastra` | a palm-leaf manuscript | leaf strips strung on a red cord, text incised and inked, a ruled-line gauge with a tick at every 10% |
| `kbach` | gold on lacquer | a *kbach* vine of curls and flame leaves between the rows, gilded numerals, gilt-edged gauge cells |

The used percentage is in Khmer numerals (០១២៣៤៥៦៧៨៩) and the time to the reset in Khmer words (ថ្ងៃ day, ម៉ោង hour, នាទី minute). Without Khmer text shaping on the machine (Pillow's raqm) the time falls back to `2d 6h`; the numerals do not need it. Everything else keeps its TokenTV meaning: the window name (`5H`, `WK`, `BUD`), `OLD` for an old reading, a dash and `NO DATA` when nothing was reported, never `0`.

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/token-tv demo --out token-tv-demo      # every face from sample data, no clock or login
.venv/bin/token-tv start --face kbach            # on the machine that talks to the clock; or pick one in the dashboard
```

## 2. Desk mode: the same screen, not for tokens

<p align="center"><img src="docs/images/desk-pages.png" width="800" alt="Clock, calendar, countdown and board pages"></p>

`token-tv desk` rotates pages that have nothing to do with AI usage: a **clock** (time in Khmer numerals, weekday, day, month and year in Khmer), a **calendar**, a **countdown** to a date you name, and a **board** that shows whatever a JSON file says, so any script, cron job or app can put anything on the screen. See [docs/desk.md](docs/desk.md).

```bash
.venv/bin/token-tv desk --init                    # writes desk.json and board.json beside your config
.venv/bin/token-tv desk --out pages               # draws every page to ./pages, no clock needed
.venv/bin/token-tv desk --device-url 192.168.0.50 # rotates the pages on your clock
.venv/bin/token-tv desk --restore                 # puts the clock's own display settings back
```

The code is in `token_tv/khmer.py`, `token_tv/kbach.py` and `token_tv/desk.py`. Fonts: Moul, Bokor, Battambang and Noto Serif Khmer (SIL OFL 1.1, licences beside them in `token_tv/web/`).

---

<h1 align="center">TokenTV</h1>
<p align="center">
  <a href="https://github.com/click6067-ship-it/token-tv/releases/latest"><img alt="Release" src="https://img.shields.io/github/v/release/click6067-ship-it/token-tv"></a>
  <a href="https://github.com/click6067-ship-it/token-tv/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <a href="https://hackaday.com/2026/10/06/smalltv-hacking-with-surprisingly-little-fuss/"><img alt="Featured on Hackaday" src="https://img.shields.io/badge/featured%20on-Hackaday-1a1a1a"></a>
  <a href="https://github.com/steipete/CodexBar#desk-display"><img alt="Listed in CodexBar" src="https://img.shields.io/badge/listed%20in-CodexBar-555555"></a>
</p>

<p align="center"><img src="https://raw.githubusercontent.com/click6067-ship-it/token-tv/main/docs/images/real-photos.jpg" width="600" alt="Digital, Sci-Fi HUD, Neon and Arcade on the real clock"> <a href="https://youtube.com/shorts/FN5DLILYiI0"><img src="https://raw.githubusercontent.com/click6067-ship-it/token-tv/main/docs/images/real-clock.gif" width="146" alt="TokenTV on a real clock (16 seconds; the full video is on YouTube)"></a></p>
<p align="center"><img src="https://raw.githubusercontent.com/click6067-ship-it/token-tv/main/docs/images/main-faces.png" width="600" alt="The four main faces: Digital, Sci-Fi HUD, Neon and Arcade (sample data)"></p>

Turn a ~$5 AliExpress clock (GeekMagic SmallTV) into a physical AI usage dashboard. No firmware flashing.

**Live demo:** [token-tv.vercel.app](https://token-tv.vercel.app)  
**YouTube:** [https://www.youtube.com/shorts/FN5DLILYiI0](https://youtube.com/shorts/FN5DLILYiI0)  
**Try it:** [live demo](https://token-tv.vercel.app) or `npx token-tv demo`, no clock or login needed.  
**Set it up:** run `npx token-tv start` (or `uvx token-tv start`) on a computer that stays on. It finds your signed-in tools and the clock on your Wi-Fi, keeps running in the background and opens your dashboard. Or tell your AI *"Set up TokenTV for me"* ([AGENTS.md](https://github.com/click6067-ship-it/token-tv/blob/main/AGENTS.md)).

**New: Arcade.** When you're coding, the bots get busy too. Codex, for example, rains code to grow flowers while it spends tokens: the more it spends, the fuller the garden. Grok refuels its rocket and, resting, gazes up at Earth, and Copilot and Anti are the newest friends.

<p align="center"><img src="https://raw.githubusercontent.com/click6067-ship-it/token-tv/main/docs/images/highlight-claude.gif" width="150" alt="Clawd breakdancing"> <img src="https://raw.githubusercontent.com/click6067-ship-it/token-tv/main/docs/images/highlight-codex.gif" width="150" alt="The Codex cloud raining code on its flowers"> <img src="https://raw.githubusercontent.com/click6067-ship-it/token-tv/main/docs/images/highlight-grok.gif" width="150" alt="Grok's rocket losing a side booster"> <img src="https://raw.githubusercontent.com/click6067-ship-it/token-tv/main/docs/images/highlight-copilot.gif" width="150" alt="Copilot drawing a heart in the sky"> <img src="https://raw.githubusercontent.com/click6067-ship-it/token-tv/main/docs/images/highlight-anti.gif" width="150" alt="Anti floating in zero gravity"></p>

**Each reacts in its own way.** with little left, one rushes and another frets. 
**And a few secret scenes.** Some come only at certain hours, some only after a bot has really worked, and some almost never. for a moment, and we're not telling you which. [The collection](https://token-tv.vercel.app/collection/) shows how much is out there.

Simple numbers at a glance, and cute while it's at it. Coding alone at 3 a.m.? Your bots are still up with you, and someone might even make you coffee. Ideas, suggestions and PRs are welcome. *Cuteness is a feature.*
