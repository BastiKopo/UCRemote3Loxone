# UC Remote 3 ↔︎ Loxone Driver

This repository provides a lightweight Python driver that bridges the
[Unfolded Circle Remote 3](https://unfoldedcircle.com/remote/) with a Loxone
Miniserver. The driver focuses on translating Remote 3 button gestures into
HTTP calls that trigger scenes, virtual inputs or any other command supported
by the Loxone REST interface.

## Features

- Declarative JSON configuration describing button/action → command mappings.
- Support for standard HTTP commands as well as the `virtual_input:<uuid>:<value>`
  helper format.
- Small and easily extensible Python package (`ucremote3loxone`).
- Comes with unit tests that demonstrate the expected behaviour of the driver.
- Discovers the functions exposed by the Loxone Miniserver so they can be
  presented within the Remote 3 web interface.

## Getting started

Create and activate a virtual environment, then install the project in editable
mode together with the testing dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### Configuration

The driver reads a JSON configuration file. Each mapping requires a button name,
an action (`single_press`, `double_press` or `long_press`) and one or more
commands to execute.

```json
{
  "miniserver_url": "http://loxone.local",
  "username": "loxone",
  "password": "secret",
  "remote_name": "Living Room Remote",
  "mappings": [
    {
      "button": "top",
      "action": "single_press",
      "commands": ["dev/sps/io/scene-uuid/on"]
    },
    {
      "button": "bottom",
      "action": "long_press",
      "commands": ["virtual_input:light-uuid:toggle"]
    }
  ]
}
```

### Using the driver

```python
from ucremote3loxone import load_config, Remote3LoxoneDriver

config = load_config("/path/to/config.json")
driver = Remote3LoxoneDriver(config)

# Example event originating from the Remote 3
driver.handle_event("top", "single_press")

# Present the available Loxone functions in your UI
functions = driver.discover_miniserver_functions()
for function in functions:
    print(function.name, function.uuid)
```

### Building an integration archive

Create a tarball that can be uploaded to the Remote 3 integration interface.
Ensure the package is importable before executing the command.  The simplest
option is to install the project in editable mode using the Python that will
invoke the packaging module:

```bash
python3 -m pip install --editable .
```

Alternatively you can temporarily add the `src/` directory to your
`PYTHONPATH` (see the platform specific sections below).

Once the package is available on the import path you can build the archive
with:

```bash
python -m ucremote3loxone.packaging
```

By default the archive is stored inside `dist/uc-remote3-loxone.tar.gz`.  The
module also exposes a `build_integration_archive` helper if you prefer to
trigger the build from your own tooling.

#### Platform-specific notes

- **Windows (PowerShell 5+ / Windows Terminal)**
  1. Öffne eine PowerShell-Eingabeaufforderung im Repository-Ordner.
  2. Stelle sicher, dass die Abhängigkeiten installiert sind (z. B. mittels
     `py -m venv .venv`, `.venv\Scripts\Activate.ps1`, `pip install -e .[dev]`).
     Alternativ kannst du für einen einmaligen Lauf das Projektverzeichnis
     vorübergehend zum Modulpfad hinzufügen:
     ```powershell
     $env:PYTHONPATH = "${PWD}/src"
     ```
  3. Führe den Verpackungsbefehl aus:
     ```powershell
     python -m ucremote3loxone.packaging
     ```
  4. Die erzeugte Datei findest du anschließend unter `dist\uc-remote3-loxone.tar.gz`. Für einen manuellen Export kannst du alternativ das integrierte `tar`-Tool verwenden:
     ```powershell
     tar -czf uc-remote3-loxone.tar.gz -C dist .
     ```

- **macOS (Terminal/Zsh)**
  1. Öffne das Terminal und navigiere in das Projektverzeichnis (`cd /Pfad/zu/UCRemote3Loxone`).
  2. Installiere die Abhängigkeiten (z. B. `python3 -m venv .venv`, `source .venv/bin/activate`, `pip install -e .[dev]`).  Falls du das
     Projekt nicht installieren möchtest, kannst du auch den `src/`-Ordner
     temporär für den laufenden Prozess verfügbar machen:
     ```bash
     export PYTHONPATH="${PWD}/src"
     ```
  3. Baue das Archiv wie unter Linux mit:
     ```bash
     python3 -m ucremote3loxone.packaging
     ```
  4. Das tarball liegt danach unter `dist/uc-remote3-loxone.tar.gz`. Bei Bedarf kannst du ein manuelles Archiv erstellen:
     ```bash
     tar -czf uc-remote3-loxone.tar.gz -C dist .
     ```

### Development

Run the unit test suite with `pytest`:

```bash
pytest
```

## License

MIT
