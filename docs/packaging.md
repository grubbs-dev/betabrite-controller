# Packaging and distribution

BetaBrite Controller 1.2.0 has three supported distribution layers:

1. Native PySide6/Qt desktop applications for normal Windows, macOS, and Linux users.
2. A standard Python wheel and source distribution for the shared backend, CLI, and development workflows.
3. The retained Fedora GTK4 installer for compatibility and reference hardware use.

The native desktop builds use Qt for Python's `pyside6-deploy` wrapper around Nuitka. Each operating system builds its own application; the project does not cross-compile platform binaries.

## Release artifacts

| Platform | Release files | Contents |
| --- | --- | --- |
| Windows x64 | standalone `.exe`, portable `.zip`, Inno Setup `.exe` | per-user installation, Start Menu shortcut, optional desktop shortcut, clean uninstall |
| macOS ARM64 | `.zip`, `.dmg` | `BetaBrite Controller.app`, Applications shortcut in the DMG |
| Linux x64 | standalone `.bin`, portable `.tar.gz` | `AppRun`, per-user desktop installer/uninstaller, desktop entry, icon |
| Python | `.whl`, `.tar.gz` | backend, CLI, and portable desktop Python modules |
| Source | project `.tar.gz`, project `.zip` | repository source and packaging inputs |
| Integrity | `SHA256SUMS-*`, `SHA256SUMS` | per-platform and combined SHA-256 manifests |

Unsigned Windows and macOS artifacts include `-unsigned` in the filename. Signed builds omit that qualifier. Linux artifacts are not Authenticode/Developer-ID signed and do not use that suffix.

Every native package contains the Python and Qt runtime. Users do not install Python, pip, Git, Qt, or compiler tooling.

## Native build entry point

Run:

```bash
python scripts/build-native.py --dry-run
python scripts/build-native.py
```

The build script:

- detects the current platform and architecture
- validates application icon inputs and Linux Python headers
- creates a fresh ignored `pysidedeploy.spec`
- supplies noninteractive Nuitka downloads
- embeds application name, version, icon, and platform metadata
- embeds the Qt runtime icon asset
- compiles on the target operating system
- executes the compiled application's `--smoke-test`
- creates platform packages and SHA-256 manifests
- validates macOS bundle metadata before distribution
- optionally notarizes signed macOS output when credentials are present

Linux native compilation requires the development headers matching the active Python. Fedora users can install them with:

```bash
sudo dnf install python3-devel
```

Generated executables, deployment directories, build trees, and deploy specs are ignored and must never be committed.

## Application branding

`assets/betabrite-controller.svg` is the editable vector source. `scripts/generate-icons.py` deterministically renders PNG sizes, the Windows `.ico`, the macOS `.icns`, the Qt runtime PNG, and the Linux desktop icon using Pillow.

Verify checked-in derivatives with:

```bash
python scripts/generate-icons.py --check
```

The mark is an original LED-matrix letter B with controller indicators. No third-party logo or artwork is used.

## Windows installer and signing

The Inno Setup definition is `packaging/windows/betabrite-controller.iss`. It installs under the current user's local application directory and normally uses no administrator privilege. Uninstall removes application files and shortcuts but deliberately leaves the user's remembered-adapter settings in the platform configuration directory.

Windows signing is optional in ordinary CI. To enable it on non-pull-request builds, configure both GitHub Actions secrets:

- `WINDOWS_CODE_SIGNING_CERTIFICATE_BASE64` — base64-encoded PKCS#12/PFX code-signing certificate containing its private key
- `WINDOWS_CODE_SIGNING_CERTIFICATE_PASSWORD` — password for that PFX

The workflow signs and timestamps the portable executable before rebuilding its ZIP, then signs and timestamps the installer. It currently uses DigiCert's RFC 3161 timestamp endpoint. An appropriate publicly trusted code-signing certificate is required for a production identity; an Extended Validation certificate may have additional hardware or cloud-key requirements that need a provider-specific signing step.

When secrets are absent, compilation and installer generation continue and filenames explicitly contain `-unsigned`.

## macOS signing and notarization

The app bundle uses:

- bundle identifier: `dev.grubbs.BetaBriteController`
- display name: `BetaBrite Controller`
- release version from `betabrite_controller.__version__`
- the generated `.icns` application icon
- utility application category and GUI bundle mode

The DMG has a basic drag-to-Applications layout. Its ZIP is created with `ditto` so bundle metadata, executable bits, symlinks, and resource forks are preserved.

For Developer ID signing, configure:

- `MACOS_DEVELOPER_ID_CERTIFICATE_BASE64` — base64-encoded PKCS#12/P12 export containing a **Developer ID Application** certificate and private key
- `MACOS_DEVELOPER_ID_CERTIFICATE_PASSWORD` — password for the P12
- `MACOS_SIGNING_IDENTITY` — full certificate identity, normally `Developer ID Application: Name (TEAMID)`

For Apple notarization with an App Store Connect API key, also configure all three:

- `APPLE_NOTARY_KEY_ID` — App Store Connect API key ID
- `APPLE_NOTARY_ISSUER_ID` — App Store Connect issuer ID
- `APPLE_NOTARY_PRIVATE_KEY_BASE64` — base64-encoded `.p8` private key

The workflow imports the Developer ID identity into an ephemeral keychain. Nuitka signs the app with hardened runtime options; the packager submits the app archive, staples the app, builds and signs the DMG, submits the DMG, and staples the result. Pull-request builds never receive or use signing credentials.

When these secrets are absent, Nuitka's required ad-hoc signature is used, notarization is skipped, and release filenames explicitly contain `-unsigned`.

## Linux portable integration

The proven Nuitka one-file `.bin` remains the primary compiled Linux output. The tar archive wraps it with:

- `AppRun` for launch from the extracted directory
- a freedesktop desktop-entry template
- a 256px hicolor icon
- `install-desktop.sh` for per-user installation
- `uninstall-desktop.sh` for application removal while preserving settings

No root privilege is required for the portable desktop installer. The Fedora GTK installer remains separate and continues to manage system udev rules and `dialout` access for the tested adapter.

An AppImage is intentionally not a v1.2.0 release artifact. The current one-file Nuitka binary already supplies the portable runtime, while adding AppImage would require downloading and executing an additional architecture-specific packaging tool in CI. That would add a second executable-container layer and an external release dependency without improving hardware access or runtime coverage. The tar package preserves a conventional AppRun/desktop/icon layout so a pinned AppImage stage can be added later if its maintenance benefit becomes clear.

## CI validation

`.github/workflows/native-desktop.yml` runs independently on `ubuntu-latest`, `windows-latest`, and `macos-latest`. Each job:

1. installs target build prerequisites
2. restores safe Nuitka/ccache data
3. compiles the application without interactive prompts
4. executes the raw compiled application with `--smoke-test`
5. creates the native packages and installer where applicable
6. executes the application again from the packaged ZIP/tar bundle
7. generates SHA-256 checksums
8. uploads platform artifacts

This proves compilation and packaged startup. It does not prove physical sign transmission on Windows or macOS.

## Tagged release workflow

`.github/workflows/release.yml` is triggered by `v*` tags. It first requires the tag version to equal the package version, runs all unit tests and the headless desktop smoke path, then builds source/Python artifacts and calls the native workflow. A final Ubuntu job downloads every platform artifact, generates and verifies a combined checksum manifest, and creates the GitHub Release.

The v1.1.0 tag and release remain immutable. A failed future release must be investigated rather than repaired by force-moving a published tag.
