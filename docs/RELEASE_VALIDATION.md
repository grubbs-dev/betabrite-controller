# Release validation — 2026-09-30

**NOT READY FOR v1.0.0 RELEASE.** That tag already exists. This work prepares the existing **1.2.0** candidate; it is **not ready for an official release** until the external gates below pass.

No tag or GitHub Release was created during this work. Initial HEAD was 424373a on chore/v1.2.0-release-prep. Release changes are committed separately for native CI validation. Pre-existing betabrite-gui changes and its backup remain local and were preserved.

## VERIFIED locally

Environment: Fedora Linux 44 x86_64. Clean source/wheel validation used a Python 3.13 virtual environment without system site packages. Native compilation used a separate clean Python 3.14.7 environment with matching system headers, PySide6/Qt 6.11.2 and Nuitka 4.2.1. CI uses Python 3.13, so its platform results remain required.

| Gate | Executed check | Result |
| --- | --- | --- |
| Clean dependencies | pip install .[desktop] in fresh environments; pip check | Pass |
| Complete tests | python -m unittest discover -s tests -v | 78 tests pass; baseline was 63 |
| Protocol regression | Exact packet-byte fixture plus fake serial framing/timeout/cleanup tests | Pass; no physical sign used |
| Settings | Platform paths, malformed recovery, atomic failure, saved-state retention tests | Pass |
| GUI responsiveness | Qt event processing during a blocked fake worker, duplicate-send protection, unplug state | Pass |
| Source GUI | python -m betabrite_controller.desktop_launcher --smoke-test | Pass, including actual Qt window and packaged licenses |
| Installed wheel | CLI version/discovery and GUI version/smoke from /tmp | Pass; no USB serial adapters detected |
| Python packages | python -m build; twine check | Wheel and sdist pass |
| Native Linux build | PATH=/tmp/betabrite-native-venv/bin:$PATH /tmp/betabrite-native-venv/bin/python scripts/build-native.py | Pass |
| AppImage metadata | appimagetool AppStream validation | Pass |
| Packaged Linux GUI | AppImage --smoke-test using offscreen, xcb and wayland | Pass from outside repository |
| Desktop integration | Install actual AppImage into temporary XDG data directory, start installed copy, desktop-file-validate | Pass |
| Integrity | sha256sum --check SHA256SUMS-linux | All three local artifacts pass |
| Workflows | actionlint 1.7.7 | Pass |
| Source hygiene | compileall, shell syntax, generate-icons.py --check, git diff --check | Pass |
| Secrets | gitleaks 8.24.3 Git scan of all 30 commits | No leaks found |
| Dependencies | pip-audit after upgrading the fresh environment's pip | No known vulnerabilities; local project has no PyPI audit record |

GUI screenshot in docs/assets/desktop.png is an actual offscreen rendering with discovery mocked empty. It is not a hardware demonstration.

The local native artifact is **dist/native/BetaBrite-Controller-1.2.0-Linux-x86_64.AppImage**, approximately 47 MB. Local BIN/tar outputs are also available for diagnostic packaging checks; they are not public release downloads. Generated files are ignored.

## IMPLEMENTED BUT REQUIRES EXTERNAL/HARDWARE VALIDATION

- Execute the revised Native Desktop workflow on the exact committed candidate. No Windows or macOS build was executed in this Linux session.
- Windows 10/11 x64: native build, installed application, Start Menu, uninstall, serial driver/device behavior and Authenticode with real credentials.
- macOS Apple Silicon: native build, bundle metadata, Finder/Applications launch, DMG install, USB serial discovery, Developer ID signing and Apple notarization with real credentials. Intel builds are not in the supported matrix.
- Linux: fresh Ubuntu 24.04 baseline installation and broader distribution testing. Local Fedora startup is verified; it is not proof of compatibility with every Linux desktop.
- Physical BetaBrite: send/visible display, effects, unplug/replug, permission failures, multiple adapters and remembered identity on each claimed platform. Prior repository hardware notes are historical evidence, not a new test of this change.
- Review bundled notices and corresponding source information for the exact native dependency inventories, including platform-specific Qt libraries.
- Review/commit the working tree, complete signing status and manual release checklist, run the remote gates, then validate downloads from the actual GitHub Release.

Use docs/RELEASING.md for the commands and gate checklist. Do not create v1.2.0 until the required gates pass, and never recreate or move v1.0.0.
