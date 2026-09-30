# Release checklist

The repository already contains v1.0.0 and v1.1.0 tags. The next prepared version is **1.2.0**. Never move or replace an existing release tag. The sole application version is betabrite_controller/__init__.py.

## Gates before tagging

- [ ] Review all changes, including any pre-existing local work; commit only intended changes.
- [ ] Clean git status; version and release notes finalized.
- [ ] Clean dependency install and pip check pass.
- [ ] Full unittest suite, compilation, actionlint and icon checks pass.
- [ ] Wheel/sdist build and twine metadata validation pass.
- [ ] Gitleaks history/worktree scan and dependency audit reviewed.
- [ ] Native Desktop workflow passes Windows, macOS and Linux jobs for the exact release commit.
- [ ] Raw and packaged Qt smoke checks pass on every target.
- [ ] Windows installer installs, starts from Start Menu and uninstalls on a clean Windows 10/11 x64 machine.
- [ ] macOS ARM64 DMG installs through Finder and starts from Applications on a clean machine.
- [ ] Linux AppImage launches through a file manager and the optional application-menu installation works on the CI baseline distribution.
- [ ] Physical BetaBrite send, effects, unplug/replug, permission failures and remembered identity checked and recorded for claimed hardware/platforms.
- [ ] Documentation matches the actual UI and supported OS/architectures.
- [ ] MIT and bundled dependency notices/source information reviewed.
- [ ] Authenticode status verified; Developer ID and notarization status verified. Explicitly document unsigned development builds.
- [ ] Release checksums generated and verified; artifact filenames match version and architecture.
- [ ] docs/RELEASE_VALIDATION.md updated with actual evidence.

## Validate the candidate

Install the documented development/build dependencies, then:

```bash
python -m pip check
python -m unittest discover -s tests -v
python -m compileall -q betabrite_controller scripts tests
python scripts/generate-icons.py --check
betabrite --version
betabrite --list-ports
betabrite-desktop --smoke-test
python -m build
python -m twine check dist/*.whl dist/*.tar.gz
python scripts/build-native.py
actionlint
gitleaks git --redact
python -m pip_audit
git diff --check
git status --short
```

On GitHub, run **Native Desktop → Run workflow** for the candidate branch. With GitHub CLI:

```bash
gh workflow run native-desktop.yml --ref chore/v1.2.0-release-prep
gh run list --workflow native-desktop.yml
gh run watch RUN_ID --exit-status
```

Push reviewed commits before dispatching; GitHub tests remote commits, not local changes. Review artifacts and complete the manual gates. Configure signing secrets documented in packaging.md before signed candidate builds.

## Cut the release only after every required gate passes

Merge the reviewed release work to main using the repository's normal PR process, then:

```bash
git switch main
git pull --ff-only
git status --short
python -c "from betabrite_controller import __version__; print(__version__)"
git tag -a v1.2.0 -m "BetaBrite Controller 1.2.0"
git push origin v1.2.0
gh run list --workflow release.yml
gh run watch RUN_ID --exit-status
gh release view v1.2.0
```

The tag triggers preflight tests, native builds and source/package validation. Only the publish job has repository write permission, and it depends on all required jobs. It uploads three platform downloads and SHA256SUMS.txt. It does not publish partial builds.

After publication, download from the actual release page, verify checksums, signing/notarization and normal installation again, and review generated release notes. Record verified architectures, hardware, and signing status. Never claim display acknowledgment from a serial write.

If a release build fails, investigate and fix it. Do not force-move an existing public tag; use the next patch version when a published version needs correction.
