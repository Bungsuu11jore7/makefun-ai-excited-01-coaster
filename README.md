# Coaster — "Survived The Drop"

A make.fun `ai-excited-01` entry: make the AI judge excited. Top 20 share $250.

## What you are looking at

This is a keepsake ticket from a roller coaster, drawn as one big scene.

High above the ticket, a huge coaster loop rises against a sunset sky
that is burning orange and red. One train is plunging down the drop,
riders with their arms thrown up in the air. A second car hangs
upside-down right at the very top of the loop — the two most thrilling
instants of the ride, caught in a single frame.

Underneath the scene sits the cream-coloured ticket stub itself. It is
stamped with the words **I SURVIVED THE DROP**, and it carries the
rider's own verdict in plain letters:

> "SCREAMED THE WHOLE WAY DOWN — BEST 90 SECONDS OF MY LIFE"

The stub also lists the ride's numbers:

- HEIGHT 91 M
- SPEED 128 KM/H
- DROP 80 DEG

The idea is simple: a personal souvenir with readable text, one obvious
subject, bold high-contrast colour, and two peak moments at once. It
should land at a glance, and it should still be legible when shrunk
down to about 300 px.

## How the picture is built

Everything is drawn by `main.py`, a renderer written in pure Python
3.13 using only the standard library. There is no PIL, no network
access, and no external font files.

The renderer is built from scratch in three parts:

- a hand-rolled RGB canvas that every shape and line is painted onto,
- a 5x7 bitmap font drawn pixel by pixel for all the ticket text,
- a hand-rolled PNG encoder built on `zlib` and `struct`.

Every mark on the image comes from fixed coordinates and fixed numbers
in the code, with no randomness and no clock or environment input. Run
it twice and you get the exact same file, byte for byte.

## Running it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

That writes `out/entry.png`: a 1024x1024 PNG, well under 1 MiB in size.

## License

MIT — see `LICENSE` for the full text.
