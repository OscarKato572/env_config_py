# env_config_py

Load configuration from the environment with type coercion.

```python
import os

from env_config_py import ConfigError, EnvConfig

os.environ["APP_PORT"] = "8080"
os.environ["APP_DEBUG"] = "yes"
os.environ["APP_HOSTS"] = "alpha, beta,gamma"

config = EnvConfig(
    schema={
        "APP_PORT": "int",
        "APP_DEBUG": "bool",
        "APP_HOSTS": "list",
        "APP_NAME": "str",
        "APP_TIMEOUT": "float",
    },
    defaults={"APP_NAME": "service", "APP_TIMEOUT": 2.5},
)

port = config.get("APP_PORT")            # 8080, an int
settings = config.get_many(["APP_NAME", "APP_DEBUG", "APP_HOSTS"])
# {"APP_NAME": "service", "APP_DEBUG": True, "APP_HOSTS": ["alpha", "beta", "gamma"]}

if "APP_TIMEOUT" in config:
    timeout = config.get("APP_TIMEOUT")  # 2.5, from the default
```

## Why this exists

The environment is a flat namespace of strings, so every service ends up
repeating the same ``int(os.environ[...])`` dance, and the boolean case is a
trap: ``bool("false")`` is ``True``. This library lets you declare a schema
once and get back typed values.

The trade-off is strictness. A missing required variable raises ``ConfigError``
and an unrecognised boolean spelling raises as well, instead of quietly
falling back to a default. That means a misconfigured deployment fails loudly
at startup rather than behaving strangely later. If you want a permissive
fallback, supply a default for the key.

## The awkward edge

Defaults are trusted Python values and are *not* coerced. If your schema says
``"list"`` and your default is the string ``"a,b"``, you get the string back,
not a list. This is deliberate: the default lives in code where you can write
the value you actually mean, and coercing it would make a default of ``0``
ambiguous between the integer zero and the string ``"0"``.

## Supported types

- ``"str"``: the raw value.
- ``"int"``: base-10 integer, surrounding whitespace allowed.
- ``"float"``: Python float syntax, including scientific notation.
- ``"bool"``: one of ``1``, ``0``, ``true``, ``false``, ``yes``, ``no``,
  ``on``, ``off``, case-insensitive.
- ``"list"``: comma-separated, each item trimmed; empty items are dropped.

## API

- ``EnvConfig(schema, defaults=None, environ=None)``: ``schema`` maps a key to
  a type name. ``defaults`` supplies values for keys that may be absent.
  ``environ`` overrides the process environment, which is useful in tests.
- ``config.get(key)``: return the coerced value, or raise ``ConfigError``.
- ``config.get_many(keys)``: return a dict of coerced values, in the order
  requested.
- ``key in config``: true when the key is in the schema and either present in
  the environment or given a default. This is a presence check, not a
  coercion check.
- ``ConfigError``: raised for unknown keys, missing required keys, unsupported
  type names, and values that fail coercion.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

