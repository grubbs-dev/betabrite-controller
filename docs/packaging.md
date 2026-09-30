# Packaging and signing

The existing pyside6-deploy / Nuitka implementation is retained. Build on the target OS; no desktop cross-compilation is used. Versioned dependency constraints live in packaging/constraints.txt.

```bash
python -m pip install -c packaging/constraints.txt ".[desktop]" Nuitka ordered-set zstandard
python scripts/build-native.py --dry-run
python scripts/build-native.py
```

Linux additionally needs a compiler, matching Python headers and patchelf. Windows installer creation uses Inno Setup 6 in the native workflow. macOS uses hdiutil and ditto.

## Outputs

Public release downloads are limited to:
- Windows x64: betabrite-controller-VERSION-windows-x86_64[-unsigned]-setup.exe
- macOS ARM64: betabrite-controller-VERSION-macos-arm64[-unsigned].dmg
- Linux x86_64: BetaBrite-Controller-VERSION-Linux-x86_64.AppImage
- SHA256SUMS.txt

Portable EXE/ZIP, BIN/tar, wheel/sdist and source archives are intermediate or CI artifacts, not extra choices on the public release. GitHub also provides its standard source archive links. The combined release checksum file lists only the three published platform downloads.

Windows uses per-user installation and uninstall, Start Menu integration and optional desktop shortcuts. The macOS DMG contains the application and an Applications shortcut. Linux AppImage launch needs no Python; its GUI can install a per-user application-menu entry.

AppImage tooling and its runtime come from versioned upstream releases, with SHA-256 values checked before execution. No floating continuous download is used. Compilation on Ubuntu 24.04 defines the CI Linux baseline; an AppImage is not a guarantee of compatibility with older libc versions.

## Smoke checks

The compiled program's --smoke-test runs from a temporary working directory to avoid source-tree resource fallback. It constructs and renders the actual Qt window offscreen, loads the packaged icon, round-trips isolated settings, and enumerates serial ports without opening them.

The native workflow additionally extracts and starts portable packages, installs/starts/uninstalls the Windows installer, mounts/starts the macOS DMG, and starts the AppImage in extract-and-run mode. These checks are implemented; their passing status must be verified in each release run. Hardware and visible desktop integration are separate manual gates.

## Windows signing

Configure GitHub secrets:
- WINDOWS_CODE_SIGNING_CERTIFICATE_BASE64: base64 PFX containing the private key
- WINDOWS_CODE_SIGNING_CERTIFICATE_PASSWORD: PFX password

The workflow signs and timestamps the app before packaging it into the installer, signs the installer, then runs signtool verify /pa. Missing credentials produce explicitly unsigned development downloads. Hardware-token/cloud-only certificates require a signing-provider integration; the PFX path does not claim to support those.

## macOS signing and notarization

Bundle identity: dev.grubbs.BetaBriteController. Application name: BetaBrite Controller.

Developer ID secrets:
- MACOS_DEVELOPER_ID_CERTIFICATE_BASE64: base64 Developer ID Application P12
- MACOS_DEVELOPER_ID_CERTIFICATE_PASSWORD
- MACOS_SIGNING_IDENTITY: full Developer ID Application certificate identity

Notarization secrets (all three required together):
- APPLE_NOTARY_KEY_ID
- APPLE_NOTARY_ISSUER_ID
- APPLE_NOTARY_PRIVATE_KEY_BASE64: base64 .p8 App Store Connect API key

The workflow imports the certificate into a temporary keychain. Nuitka applies the identity/hardened-runtime settings; packaging verifies the bundle, submits/staples the app, then signs, submits and staples the DMG. Temporary credential files and keychains are removed in an always-running cleanup step. PR builds do not use signing secrets.

Without Developer ID credentials, builds are ad-hoc-signed by the platform toolchain and labeled unsigned. Developer ID signing without notary credentials does not imply notarization. Check the workflow log and Gatekeeper assessment before declaring either successful.

## Third-party distribution

The Licenses dialog reads license texts embedded in the wheel and native runtime. THIRD_PARTY_NOTICES.md identifies upstream source locations. Confirm notices against the exact dependency inventory for each platform, including Qt third-party libraries. Source and build instructions permit rebuilding with modified dependencies. Do not bundle proprietary USB drivers.

See [the release checklist](RELEASING.md). No tag or release should be published solely because source tests pass.
