# Demo video pipeline

A reproducible, fully-offline pipeline that produces [`demo.mp4`](demo.mp4) — a narrated
~3:11 walkthrough of the solution. **Every figure on screen is real program output**: the
terminal scenes are rebuilt from genuine captured runs (`assets/runs.json`) and the
human-gate scene embeds an actual screenshot of the loan-officer desk.

> Honesty note: terminal "footage" is re-typeset from the real run data (captured by
> `capture_data.py`) for legibility at 1080p — the numbers, decisions, timelines, and
> exceptions are exactly what the agents produced. The UI scene is a real Chrome screenshot.

## How it's made

1. **`capture_data.py`** — runs the headline personas + the durable inbox flow through the
   real agent graph and writes the genuine results to `assets/runs.json`.
2. **`make_scenes.py`** — generates 10 on-brand 1920×1080 HTML scenes (`scenes/`) from that
   data + a narration `manifest.json`.
3. **Screenshots** — each scene is rendered to a PNG (`frames/`) with headless Chrome; the
   web-UI scene reuses a real screenshot in `assets/shots/`.
4. **`assemble.py`** — narrates each scene with macOS `say`, then muxes still + audio per
   scene with `ffmpeg` and concatenates to `demo.mp4`.

## Regenerate

```bash
# from the repo root, with the dev venv active and ffmpeg + macOS `say` available
python video/capture_data.py
python video/make_scenes.py
# render scene PNGs (headless Chrome):
for f in video/scenes/*.html; do
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
    --hide-scrollbars --force-device-scale-factor=1 --window-size=1920,1080 \
    --user-data-dir=/tmp/cshot --screenshot="video/frames/$(basename ${f%.html}).png" \
    "file://$(python -c "import urllib.parse,os,sys;print(urllib.parse.quote(os.path.abspath(sys.argv[1])))" "$f")"
done
python video/assemble.py          # → video/demo.mp4   (DEMO_VOICE=Samantha by default)
```

## For submission

Upload `demo.mp4` to YouTube/Vimeo (unlisted is fine) and put the link in the Devpost
submission. It is 1920×1080, H.264 + AAC, ~3:11 (well under the 5-minute limit). Narration
script lives in `manifest.json`; the shot list / timing is in `../docs/DEMO_SCRIPT.md`.

`audio/` and `clips/` are regenerable intermediates (git-ignored).
