# Pixel Studio Protocol Notes

These notes document the protocol surface used by Pixel Studio. They separate
confirmed Alpha/BetaBrite protocol behavior from assumptions that still require
physical sign validation.

## Sources

- Adaptive Micro Systems, **Alpha Sign Communications Protocol 9708-8061F**,
  March 10, 2006: https://www.alpha-american.com/alpha-manuals/M-Protocol.pdf
- The project dependency `alphasignpy==0.1.1`, inspected locally, implements
  packet framing, checksums, TEXT files, and SMALL DOTS PICTURE files using the
  same command codes described by the protocol manual.

## Confirmed Mechanism

Pixel Studio uses **SMALL DOTS PICTURE** files.

- Write command: `I` (`49H`)
- Read command: `J` (`4AH`) is documented but not exposed in this release.
- Display mechanism: a normal TEXT file calls a stored SMALL DOTS PICTURE with
  control code `14H` followed by the picture file label.
- Maximum documented SMALL DOTS size: **31 rows x 255 columns**.
- Width and height are encoded as two ASCII hexadecimal bytes each.
- The sign requires at least a 100 ms pause after the width bytes and before row
  pattern data. `alphasignpy` represents this internally with its `DELAY` marker;
  the serial sender strips the marker and sleeps.
- Each row is represented by one ASCII pixel-color character per column and is
  terminated with carriage return (`0DH`).
- The packet checksum is the 16-bit sum from `STX` through `ETX`, encoded as
  four uppercase ASCII hexadecimal digits. Existing `alphasignpy` packet
  framing is used for this.

## Pixel Colors

The protocol defines these SMALL DOTS pixel color characters:

| Character | Color |
| --- | --- |
| `0` | Off |
| `1` | Red |
| `2` | Green |
| `3` | Amber |
| `4` | Dim red |
| `5` | Dim green |
| `6` | Brown |
| `7` | Orange |
| `8` | Yellow |

Pixel Studio stores only these protocol-compatible colors.

## One-Line BetaBrite Assumptions

The application defaults to **90 x 7** pixel documents for compatibility with
classic one-line BetaBrite-style signs and the existing project hardware notes.
The protocol can encode taller SMALL DOTS files up to 31 rows, but this release
does not claim every BetaBrite model can display every supported protocol size.

The established serial path remains:

- Address: `00`
- Type code: `Z` (all signs)
- Serial: 9600 baud, 7 data bits, even parity, 1 stop bit, DTR disabled

## Static Transmission Sequence

For a static frame, Pixel Studio sends two protocol packets:

1. Write a SMALL DOTS PICTURE file to label `A`.
2. Write the priority TEXT file (`0`) containing `14H` + `A`, in HOLD mode, so
   the sign displays the stored picture.

This is deterministic and unit tested with exact byte fixtures.

## Animation

The manual confirms storage of individual SMALL DOTS PICTURE files. This release
also supports local multi-frame editing and local Qt timer playback.

Native sign-side timed animation of arbitrary custom DOTS frames has **not**
been proven for the supported one-line BetaBrite path. The protocol layer can
encode multiple frames into separate DOTS labels, but the UI does not advertise
native upload of a timed animation sequence as a supported hardware feature.

Computer-driven real-time streaming is intentionally left for future live mode
work and is separate from native stored sign animation.

## Delete/Replace

Replacing a graphic is supported by writing a new SMALL DOTS PICTURE to the same
label. A standalone delete command is not exposed because deletion appears to be
handled through model-specific memory configuration rather than a simple proven
SMALL DOTS delete packet.

## Future Live Mode API

The extension point is `betabrite_controller.live.FrameSource`:

```text
FrameSource -> simulation/update -> PixelFrame -> renderer/protocol encoder -> transport
```

Future Dino, Snake, Pong, clock, system monitor, and visualizer features should
produce `PixelFrame` objects without depending on Pixel Studio widgets.

## Live Mode Safety

The proven custom graphics path writes SMALL DOTS PICTURE files. The researched
documentation and dependency implementation do not prove that repeated writes to
those files target volatile RAM. They may use persistent sign file storage.

For that reason, Live Mode does **not** rapidly stream physical frames through
the SMALL DOTS file-write path. Virtual preview, simulated transports, and
benchmark reporting are supported, but physical live framebuffer output is
blocked until a protocol-correct volatile update mechanism is proven for the
target sign.
