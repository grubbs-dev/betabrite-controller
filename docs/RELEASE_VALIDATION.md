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

## VERIFIED in GitHub Actions

Runtime code commit: **008e31f5901211d3aeab761b7d8bb89792569409**.

- [CI run 36732421639](https://github.com/grubbs-dev/betabrite-controller/actions/runs/36732421639): all 12 jobs passed. This includes Python 3.12/3.13 core tests on Windows/macOS/Linux, all three desktop jobs, wheel/sdist validation, workflow lint, secret scanning and dependency auditing.
- [Native Desktop run 36732431255](https://github.com/grubbs-dev/betabrite-controller/actions/runs/36732431255): all three jobs passed on Windows 2022 x64, macOS 15 ARM64 and Ubuntu 24.04 x86_64, using Python 3.13.
- Windows: compiled EXE, portable ZIP smoke, Inno installer creation, unattended installation, installed application smoke and uninstall all passed.
- macOS: compiled app, metadata validation, ZIP extraction/startup, DMG creation, mount/startup and unmount all passed.
- Linux: compiled binary, AppImage/AppStream generation, tar extraction/startup, AppImage offscreen and X11/Xvfb checks all passed.

The first Windows run exposed two host-path assumptions. They were corrected in 008e31f, and all tests were retained. No repository signing secrets were configured; Windows and macOS artifacts are explicitly unsigned, and no notarization succeeded or was claimed.

GUI screenshot in docs/assets/desktop.png is an actual offscreen rendering with discovery mocked empty. It is not a hardware demonstration.

The local native artifact is **dist/native/BetaBrite-Controller-1.2.0-Linux-x86_64.AppImage**, approximately 47 MB. Local BIN/tar outputs are also available for diagnostic packaging checks; they are not public release downloads. Generated files are ignored.

## IMPLEMENTED BUT REQUIRES EXTERNAL/HARDWARE VALIDATION

- Rerun native gates if runtime/build inputs change after the verified candidate.
- Windows 10/11 x64: hands-on Start Menu and installer acceptance, serial driver/device behavior and Authenticode with real credentials. Automated installer/startup/uninstall checks passed in CI.
- macOS Apple Silicon: hands-on Finder/Applications installation, USB serial behavior, Developer ID signing and Apple notarization with real credentials. Automated bundle/DMG checks passed in CI. Intel builds are not in the supported matrix.
- Linux: hands-on file-manager/menu acceptance and broader distribution testing. Ubuntu 24.04 CI and local Fedora startup are verified; this is not proof of compatibility with every Linux desktop.
- Physical BetaBrite: send/visible display, effects, unplug/replug, permission failures, multiple adapters and remembered identity on each claimed platform. Prior repository hardware notes are historical evidence, not a new test of this change.
- Review bundled notices and corresponding source information for the exact native dependency inventories, including platform-specific Qt libraries.
- Resolve the user's pre-existing GTK changes before producing a clean release checkout, complete signing status and the manual release checklist, then validate downloads from the actual GitHub Release. No release has been published.

Use docs/RELEASING.md for the commands and gate checklist. Do not create v1.2.0 until the required gates pass, and never recreate or move v1.0.0.
