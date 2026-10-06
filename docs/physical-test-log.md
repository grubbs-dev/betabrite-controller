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

Pixel Studio previously defaulted to SMALL DOTS label `A`, then wrote Priority TEXT file `0` containing `0x14` plus graphic label `A` to display that graphic. Physical graphics are now validated only after explicit memory configuration that allocates a DOTS file first.

Most likely root cause for a sign showing only `A`:

Pixel Studio's earlier graphics path wrote/invoked a DOTS graphic without first configuring a DOTS file in the sign's memory directory. Because the DOTS label was not allocated, the wrapper rendered the literal label (`A`) instead of a graphic. The problem was amplified when the wrapper lived in Priority TEXT file `0`, which masked ordinary TEXT files until the priority file was stopped.

Other considered explanations, ranked lower:

1. A DOTS/text label collision contributed to ambiguity in the first test, but the confirmed failure was missing DOTS memory setup.
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

Pixel Studio graphics display no longer uses Priority TEXT file `0` as the wrapper. Physical graphics sends must verify a compatible DOTS allocation before sending, store the graphic in DOTS `D`, then write normal TEXT wrapper label `B` that calls the graphic with `14H` + `D`. `text_label="0"` is rejected by the graphics encoder.

## Physical Graphics Validation

Operation: one 7 x 7 diagnostic SMALL DOTS graphic, green `X` pattern, stored once as DOTS file `A`, then displayed through normal TEXT wrapper `B` containing `14H` + `A`.

Physical result: FAIL. The sign alternated between `GREEN OK` and literal `A`. No 7 x 7 green `X` appeared.

Interpretation: normal TEXT file `B` was active, but the `14H` + `A` sequence was not honored as a SMALL DOTS call on this physical sign state. The `14H` control byte appeared to be ignored or unsupported, leaving the printable graphic label `A`. The stored DOTS file may exist; it was left untouched after the failed display test.

Cleanup: normal TEXT file `B` was overwritten once with `GREEN OK`, HOLD mode, fixed green, to remove the `14H` + `A` graphic reference without deleting or rewriting the SMALL DOTS file.

## Physical Graphics Validation With Allocated DOTS

Stage A: wrote one memory configuration containing TEXT `A`, TEXT `B`, TEXT `C`, and DOTS `D` (`07 x 07`, 3-color status `2000`). Read-only `F$` returned:

```text
E$AAU0100FF00BAU00ABFF00CAU00ABFF00DDU07072000
```

Checksum: PASS (`0AAE`).

Stage B: rewrote TEXT `A` once with `GREEN OK`, HOLD mode, fixed green. Physical normal text remained healthy.

Stage C: wrote one 7 x 7 green `X` to DOTS `D`, then read it back with `JD`. The response checksum passed (`0B05`) and the returned matrix exactly matched:

```text
2000002
0200020
0020200
0002000
0020200
0200020
2000002
```

Stage D: wrote normal TEXT wrapper `B`, HOLD mode, containing `14H` + `D`. Physical result: PASS. The sign alternated between `GREEN OK` and the correctly rendered green 7 x 7 `X`.

Read-only run-sequence query `F.` returned:

```text
E.TUABC
```

Checksum: PASS (`01E7`). The sign currently runs TEXT files `A`, `B`, and `C` in the default/timed run sequence, explaining why the normal text and graphic wrapper alternate.

## Memory Configuration Preflight

The prepared rollback packet restores the previous memory directory/layout only.
It does not restore previous TEXT file contents. Existing TEXT contents may be
destroyed by memory reconfiguration and must be rewritten separately after any
configuration change.

## Stop State

No Live Mode, Dino, benchmark, fuzzing, repeated graphics writes, SMALL DOTS delete, or automatic rollback commands were sent during this diagnostic. Physical normal text is validated, and physical custom graphics are validated on the tested BetaBrite/Alpha 213C-1 Series B when the DOTS file is explicitly allocated first.
