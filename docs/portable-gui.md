# Desktop architecture

The authoritative desktop product is the cross-platform Qt application. See [the user guide](USER_GUIDE.md) for features and [development](DEVELOPMENT.md) for its component boundaries.

The historical GTK interface remains available as a compatibility reference. It shares the controller and does not define the official release workflow.

Source and compiled smoke tests now initialize the real Qt GUI offscreen, render its window, load its icon, round-trip isolated configuration, and enumerate ports without opening serial hardware. They do not prove visible desktop integration or physical display operation; those remain release checklist items.
