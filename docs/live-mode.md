# Live Mode

Live Mode runs generated framebuffer applications through the same
`PixelFrame` model used by Pixel Studio.

```text
FrameSource -> simulation/update -> PixelFrame -> renderer -> transport
```

The first source is an original tiny endless runner. It is inspired by the broad
idea of a side-scrolling obstacle runner, but it uses original 7-pixel artwork
and game tuning for one-line BetaBrite-style displays.

## Dino Runner

Open **Live Mode** and choose **Original tiny runner**.

- **Start** runs the game in the local preview.
- **Space** or **Up** jumps.
- **R** restarts after a collision.
- **Escape** stops Live Mode.

The game logic is headless and deterministic when seeded. It supports gravity,
jump velocity, obstacle scrolling, collision detection, increasing speed, score
marks, game-over state, and restart without restarting the application.

## Preview Rate vs Sign Rate

The preview simulation is independent of physical sign transmission. The
application can update the local game preview at a smoother rate while a future
safe sign transport could run at a much lower measured output FPS.

Live Mode tracks:

- frames rendered
- frames transmitted
- dropped preview frames
- coalesced transmit frames
- render, encode, transport, and total latency
- scheduler lateness
- transport errors

Stale frames are coalesced instead of queued. Live Mode never builds an
unbounded backlog of historical frames.

## Hardware Safety

The researched BetaBrite custom graphics path writes **SMALL DOTS PICTURE
files** and then references those files from TEXT files. Physical testing on the
tested BetaBrite 213C-1 Series B has not yet proven the TEXT-file invocation
mechanism: `14H` + graphic label rendered as literal text instead of the stored
graphic. The available documentation and the current implementation also do
**not** prove that repeated writes target volatile RAM.

Because the write path may use persistent sign file storage, BetaBrite
Controller **does not use SMALL DOTS writes for rapid physical Live Mode
streaming**. Hardware safety takes priority over making the runner appear on the
sign.

Until a protocol-correct volatile framebuffer/update method is proven for a
specific compatible sign, Live Mode physical output remains blocked and clearly
shows **VIRTUAL PREVIEW ONLY**.

## Benchmarking

The Live Mode benchmark tools currently support virtual benchmark patterns:

- static repeat
- alternating frame
- full-width moving marker

The benchmark records target FPS, achieved FPS, bytes per frame, protocol
overhead, latency percentiles, dropped frames, failures, and a conservative
recommended FPS for simulated output.

Physical Live Mode benchmarking intentionally returns a blocked safety report
instead of repeatedly writing DOTS files to a sign.

CLI examples:

```bash
betabrite --live-benchmark-virtual --benchmark-report diagnostics/live-virtual.json
betabrite --live-benchmark-blocked-report --port COM7
```

Do not interpret virtual FPS as physical sign FPS. A physical update rate should
only be recommended after a safe volatile transport is confirmed and benchmarked.
