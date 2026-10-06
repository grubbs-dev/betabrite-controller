# Physical BetaBrite Diagnostic Log

## 2026-10-06 Recovery Trace

- Application commit/version: `5b4794a` / `v1.4.0` before local diagnostic changes
- Local tree during diagnostic: uncommitted trace/diagnostic changes added after inspection
- OS: Fedora Linux, kernel `7.1.3-201.fc44.x86_64`
- Adapter: Prolific Technology, Inc. ATEN Serial Bridge
- USB VID:PID: `067b:23a3`
- USB serial number: `AQCLb2A4517`
- Kernel driver: `pl2303`
- Device path: `/dev/ttyUSB0`
- Stable device links: `/dev/betabrite`, `/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_AQCLb2A4517-if00-port0`
- Ownership/permissions: `root:dialout`, `crw-rw----`
- Exclusive access: `lsof /dev/ttyUSB0` and `fuser -v /dev/ttyUSB0` showed no owning process
- Basic serial access: no-transmit open/close succeeded
- Application serial settings: `9600` baud, `7E1`, DTR off, timeout `1s`, write timeout `5s`

## Protocol Finding

The normal text path is unchanged from `v1.0.0` through `v1.4.0` except for device discovery/error handling around the same encoder. It writes a TEXT file with file label `A`. The literal byte `0x41` appears twice at the start of a normal text command body: once as the `WRITE_TEXT` command and once as text file label `A`.

Pixel Studio previously defaulted to SMALL DOTS label `A`, then wrote Priority TEXT file `0` containing `0x14` plus graphic label `A` to display that graphic. Physical graphics remain unverified.

Most likely root cause for a sign showing only `A`:

Pixel Studio's graphics display wrapper wrote Priority TEXT file `0` with a SMALL DOTS call to graphic `A`. If the call byte was ignored or the DOTS file was unusable, the printable residue was `A`. Because Priority TEXT file `0` masks ordinary TEXT files, subsequent normal text writes to file `A` completed but did not become visible until Priority TEXT file `0` was stopped.

Other considered explanations, ranked lower:

1. A DOTS/text label collision or missing graphics memory setup caused the sign to render residual label data instead of graphic content.
2. Serial framing/parity mismatch during an attempted write caused the sign to accept only a small residue of the command.
3. A current normal-text encoder regression is unlikely; historical text packet structure matches the released path.

## Recovery Packet

Operation: minimal known-good text write, message `TEST`, mode `hold`, color `auto`, address `00`, type `Z`.

Encoded packet bytes, including `alphasignpy` pseudo-delay marker:

```text
00 00 00 00 00 01 5a 30 30 02 ff 41 41 1b 26 62 1c 43 54 45 53 54 03 30 32 43 39 04
```

Escaped encoded packet:

```text
\x00\x00\x00\x00\x00\x01Z00\x02\xffAA\x1b&b\x1cCTEST\x0302C9\x04
```

Actual serial wire chunks transmitted by `alphasignpy`; `0xff` is not written and instead causes a 100 ms pause:

```text
00 00 00 00 00 01 5a 30 30 02
41 41 1b 26 62 1c 43 54 45 53 54 03 30 32 43 39 04
```

Physical send result: serial write completed once with no local error. Visual result remained masked by Priority TEXT file `0` until the priority file was stopped.

## Priority TEXT Recovery

Operation: documented Priority TEXT file `0` stop packet. This does not write SMALL DOTS graphics and does not reallocate sign memory.

```text
00 00 00 00 00 01 5a 30 30 02 41 30 04
```

Physical result: after one send, the sign displayed the previously written `TEST` text. This confirms normal text file `A` had been written successfully and was hidden behind active Priority TEXT file `0`.

## Normal Text Validation

Operation: normal text write to file `A`, message `GREEN OK`, `hold` mode, fixed green.

Encoded packet bytes, including `alphasignpy` pseudo-delay marker:

```text
00 00 00 00 00 01 5a 30 30 02 ff 41 41 1b 26 62 1c 32 47 52 45 45 4e 20 4f 4b 03 30 33 41 33 04
```

Actual serial wire chunks:

```text
00 00 00 00 00 01 5a 30 30 02
41 41 1b 26 62 1c 32 47 52 45 45 4e 20 4f 4b 03 30 33 41 33 04
```

Physical result: PASS. The sign displayed exactly `GREEN OK` in steady green.

## Code Fix

Pixel Studio graphics display no longer uses Priority TEXT file `0` as the wrapper. The graphics sequence now first sends the documented Priority TEXT stop packet, stores one SMALL DOTS file, then writes a normal TEXT wrapper label `B` that calls the graphic. `text_label="0"` is rejected by the graphics encoder.

## Physical Graphics Validation

Operation: one 7 x 7 diagnostic SMALL DOTS graphic, green `X` pattern, stored once as DOTS file `A`, then displayed through normal TEXT wrapper `B` containing `14H` + `A`.

Physical result: FAIL. The sign alternated between `GREEN OK` and literal `A`. No 7 x 7 green `X` appeared.

Interpretation: normal TEXT file `B` was active, but the `14H` + `A` sequence was not honored as a SMALL DOTS call on this physical sign state. The `14H` control byte appeared to be ignored or unsupported, leaving the printable graphic label `A`. The stored DOTS file may exist; it was left untouched after the failed display test.

Cleanup: normal TEXT file `B` was overwritten once with `GREEN OK`, HOLD mode, fixed green, to remove the `14H` + `A` graphic reference without deleting or rewriting the SMALL DOTS file.

## Memory Configuration Preflight

The prepared rollback packet restores the previous memory directory/layout only.
It does not restore previous TEXT file contents. Existing TEXT contents may be
destroyed by memory reconfiguration and must be rewritten separately after any
configuration change.

## Stop State

No Live Mode, Dino, benchmark, fuzzing, repeated graphics writes, SMALL DOTS delete, or memory reallocation commands were sent during this diagnostic. Physical normal text is validated; physical graphics display is not validated.
