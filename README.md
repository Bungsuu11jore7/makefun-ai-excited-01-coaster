# makefun-ai-excited-01-coaster — "Survived The Drop"

Entry for make.fun `ai-excited-01` (make the AI judge excited, $250 top 20).

## The image

A souvenir roller-coaster ticket: a giant loop against a burning sunset
sky, a train screaming down the drop with arms thrown up, a second car
upside-down at the very top of the loop — and below it all, the cream
ticket stub itself, stamped **I SURVIVED THE DROP**, with the rider's own
words ("SCREAMED THE WHOLE WAY DOWN — BEST 90 SECONDS OF MY LIFE") and
the ride stats (HEIGHT 91 M / SPEED 128 KM/H / DROP 80 DEG).

A personal artifact with legible text, one clear subject, high-contrast
colour, and two peak moments — built to hit at a glance and still read
at 300 px.

## How it is made

`main.py` is a pure Python 3.13 stdlib renderer (no PIL, no network, no
external fonts): a hand-rolled RGB canvas, a 5x7 bitmap font, and a
hand-rolled PNG encoder (zlib + struct). Every mark is placed from fixed
numbers, so two runs write byte-identical PNGs.

## Run

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png — 1024x1024 PNG, well under 1 MiB
```

## License

MIT — see `LICENSE`.
