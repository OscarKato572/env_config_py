"""Load configuration from the environment with type coercion.

The environment is a flat namespace of strings. Applications almost always
want typed values (ints, bools, floats, lists), so this module provides a
small, dependency-free way to declare a schema and read it back.

Design decision: a missing variable raises ``ConfigError`` unless a default
is supplied. Silent fallbacks hide deployment mistakes, and the explicit
default makes the intended value visible at the call site.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence


class ConfigError(ValueError):
    """Raised when a required variable is missing or cannot be coerced."""


_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _coerce_bool(raw: str) -> bool:
    """Coerce a string to bool.

    The accepted spellings are the ones humans actually type in shell
    profiles and container manifests. Anything else is an error rather than a
    silent truthy value, because ``bool("false")`` is ``True`` and that bug is
    hard to spot.
    """
    lowered = raw.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ConfigError(f"cannot interpret {raw!r} as a boolean")


def _coerce_int(raw: str) -> int:
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"cannot interpret {raw!r} as an integer") from exc


def _coerce_float(raw: str) -> float:
    try:
        return float(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"cannot interpret {raw!r} as a float") from exc


def _coerce_str(raw: str) -> str:
    return raw


def _coerce_list(raw: str) -> List[str]:
    """Split on commas and trim each item.

    Empty items are dropped so that trailing commas and whitespace-padded
    lists behave the way people expect from shell-style configuration.
    """
    return [item.strip() for item in raw.split(",") if item.strip()]


_COERCERS: Dict[str, Callable[[str], Any]] = {
    "str": _coerce_str,
    "int": _coerce_int,
    "float": _coerce_float,
    "bool": _coerce_bool,
    "list": _coerce_list,
}


class EnvConfig:
    """Read typed configuration values from the environment.

    The schema is a mapping of key to type name. Supported type names are
    ``"str"``, ``"int"``, ``"float"``, ``"bool"`` and ``"list"``. Defaults
    are optional per key; a key without a default is required.

    The ``environ`` argument exists so tests can pass a plain dict instead of
    mutating the real process environment.
    """

    def __init__(
        self,
        schema: Mapping[str, str],
        defaults: Optional[Mapping[str, Any]] = None,
        environ: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._schema: Dict[str, str] = {}
        for key, type_name in schema.items():
            if type_name not in _COERCERS:
                raise ConfigError(f"unsupported type {type_name!r} for key {key!r}")
            self._schema[key] = type_name

        self._defaults: Dict[str, Any] = dict(defaults or {})
        unknown_defaults = set(self._defaults) - set(self._schema)
        if unknown_defaults:
            raise ConfigError(
                "defaults supplied for unknown keys: "
                + ", ".join(sorted(unknown_defaults))
            )

        # ``os.environ`` is a mapping, so we can accept it directly. Copying
        # keeps the object stable if the caller mutates their dict later.
        self._environ: Mapping[str, str] = (
            dict(environ) if environ is not None else dict(os.environ)
        )

    def get(self, key: str) -> Any:
        """Return the coerced value for ``key``.

        Raises ``ConfigError`` if the key is not in the schema, is missing and
        has no default, or fails coercion.
        """
        if key not in self._schema:
            raise ConfigError(f"unknown configuration key {key!r}")

        if key in self._environ:
            raw = self._environ[key]
            coercer = _COERCERS[self._schema[key]]
            try:
                return coercer(raw)
            except ConfigError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                raise ConfigError(
                    f"cannot coerce {key!r} value {raw!r} to {self._schema[key]}"
                ) from exc

        if key in self._defaults:
            return self._defaults[key]

        raise ConfigError(f"missing required configuration key {key!r}")

    def get_many(self, keys: Sequence[str]) -> Dict[str, Any]:
        """Return coerced values for several keys.

        The order of ``keys`` is preserved in the returned dict (Python 3.7+
        dict ordering), which makes logging the result readable.
        """
        return {key: self.get(key) for key in keys}

    def __contains__(self, key: object) -> bool:
        """Report whether ``key`` is present in the environment or defaults.

        This is a presence check, not a coercion check: a key whose value is
        malformed still reports ``True``.
        """
        if not isinstance(key, str) or key not in self._schema:
            return False
        return key in self._environ or key in self._defaults
