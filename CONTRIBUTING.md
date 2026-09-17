# Contributing

Thanks for helping improve BetaBrite Controller.

## Development setup

```bash
git clone https://github.com/grubbs-dev/betabrite-controller.git
cd betabrite-controller
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The GTK4 GUI also requires the Fedora system packages installed by `install.sh`, including `python3-gobject` and `gtk4`.

## Before opening a pull request

Run the backend tests:

```bash
bash test.sh
```

Then run the lightweight source checks used by CI:

```bash
bash -n install.sh uninstall.sh test.sh scripts/build-release.sh
python3 -m py_compile betabrite betabrite-gui betabrite_controller/*.py tests/*.py
```

Keep hardware-specific claims precise. If a sign or adapter has not been physically tested, describe it as unverified rather than supported.

## Pull requests

Keep changes focused and explain:

- what changed
- why it changed
- how it was tested
- whether physical sign hardware was used during testing

Changes to serial behavior, wiring guidance, udev rules, or installation logic should include enough detail to reproduce the test environment.
