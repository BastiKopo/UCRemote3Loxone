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
Ensure the package is importable (for example by running `pip install -e .`)
before executing the command:

```bash
python -m ucremote3loxone.packaging
```

By default the archive is stored inside `dist/uc-remote3-loxone.tar.gz`.  The
module also exposes a `build_integration_archive` helper if you prefer to
trigger the build from your own tooling.

### Development

Run the unit test suite with `pytest`:

```bash
pytest
```

## License

MIT
