# Using BetaBrite Controller

Power on the sign and connect the cable. Automatic discovery prefers a remembered adapter, then the historically tested PL2303GT, then a single USB serial adapter. Ambiguous adapters require selection. A missing remembered adapter will not silently redirect an automatic send to another sign.

**Refresh / Reconnect** checks whether the selected serial port can open. **Manual port…** accepts an OS port name such as COM4, /dev/cu.usbserial-XXXX, /dev/ttyUSB0 or /dev/ttyACM0. **Use selected adapter** remembers USB VID/PID and serial number where available, so a changed port name can be followed. Adapters without unique serial numbers may require explicit selection after replugging.

**Save sign as…** assigns a friendly name. Select that name in the saved-sign list to reconnect. Reusing a name updates its configuration. Multiple signs can be saved, but only one serial operation runs at a time. Other programs should not open that same port while sending.

Type your message, select a color, mode and speed, and optionally enable flash or wide text. A special effect replaces the selected display mode. Presets only fill the editor: they do not send automatically. Non-ASCII characters are shown as question marks on the established encoding path; the character indicator warns about this. Control characters are rejected.

Click **Send to Sign**. The application stays responsive while it writes, and prevents overlapping operations. A success message confirms the serial write, not a display acknowledgment. Verify the physical sign. Unplugging during a send produces an error; reconnect and use Refresh / Reconnect.

**Save message…** stores the entire editor configuration under a name. Reusing a name updates it. The library also keeps the 20 most recent successful transmissions. Select an entry to restore it; **Delete saved message** removes the selected saved favorite. Editor state is saved on close. Invalid or corrupt stored entries are safely ignored.

**About / Diagnostics** shows version, MIT license, repository, operating system, ports and log location. Logs rotate after 1 MB and retain three backups. No message text is intentionally logged and nothing is uploaded.

Preferences live in:
- Windows: %APPDATA%/BetaBrite Controller/settings.json
- macOS: ~/Library/Application Support/BetaBrite Controller/settings.json
- Linux: ~/.config/betabrite-controller/settings.json, or XDG_CONFIG_HOME/betabrite-controller

Logs are in a logs subdirectory of the same folder. Advanced users can override the configuration directory with BETABRITE_CONFIG_DIR. Installation directories never store mutable user state.
