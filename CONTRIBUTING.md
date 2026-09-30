# Contributing

Use the isolated environment in [Development](docs/DEVELOPMENT.md). The authoritative desktop interface is Qt; GUI and CLI share the established controller.

Before submitting a change, run the full unittest suite, desktop smoke test and compilation checks. For packaging changes, build and smoke-test the native output on the appropriate OS. For workflow changes, run actionlint. Keep protocol behavior and hardware claims precise; a mocked transport test is not a physical sign test.

Describe the problem, resulting behavior, tests performed, and whether hardware was used. Do not commit credentials, compiled applications, deployment specs or virtual environments. Existing local user changes must be preserved.

The project is MIT licensed; contributions are submitted under that license. Dependencies retain their own licenses. Follow the [release checklist](docs/RELEASING.md) before tagging.
