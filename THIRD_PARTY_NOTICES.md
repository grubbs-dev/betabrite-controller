# Third-party components

BetaBrite Controller's own source is MIT licensed. Native distributions include Python and third-party libraries with separate licenses:

| Component | License | Source |
| --- | --- | --- |
| CPython | Python Software Foundation License | https://github.com/python/cpython |
| PySide6, Shiboken6 and Qt Core/Gui/Widgets | LGPLv3 (with upstream alternative licenses) | https://code.qt.io/pyside/pyside-setup.git and https://code.qt.io/qt/qtbase.git |
| pyserial | BSD | https://github.com/pyserial/pyserial |
| alphasignpy | MIT | https://pypi.org/project/alphasignpy/ |
| Pillow (transitive dependency) | HPND | https://github.com/python-pillow/Pillow |
| Nuitka runtime | Apache-2.0, see upstream exceptions | https://github.com/Nuitka/Nuitka |
| AppImage runtime | MIT, with bundled-component notices | https://github.com/AppImage/type2-runtime |

The application does not prohibit modifying or reverse-engineering LGPL components for debugging modifications. Build scripts and source are provided so the application can be rebuilt with a modified Qt/PySide distribution. Do not assume an MIT license on this application replaces dependency obligations.

Release maintainers must include dependency license texts and corresponding source/access information for the exact bundled versions, including Qt's third-party components. Review the packaged notices and dependency inventory before distribution; see docs/RELEASING.md. No proprietary serial drivers are bundled.
