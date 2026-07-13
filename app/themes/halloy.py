from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Mapping

from app.themes.colors import RGBA, from_hex


SCHEMA_VERSION = "halloy-supported-v1"


class ThemeParseError(Exception):
    def __init__(self, message: str, *, source: str = "", cause: Exception | None = None) -> None:
        super().__init__(message)
        self.source = source
        self.field_path = ""
        self.cause = cause

    def __str__(self) -> str:
        if self.field_path:
            return (
                f"{self.source}: {self.field_path}: {self.args[0]}"
                if self.source
                else f"{self.field_path}: {self.args[0]}"
            )
        return f"{self.source}: {self.args[0]}" if self.source else str(self.args[0])


class ThemeSchemaError(ThemeParseError):
    def __init__(
        self,
        message: str,
        *,
        source: str = "",
        field_path: str = "",
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, source=source, cause=cause)
        self.field_path = field_path


class ThemeColorError(ThemeParseError):
    def __init__(
        self,
        message: str,
        *,
        source: str = "",
        field_path: str = "",
        raw_value: str = "",
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, source=source, cause=cause)
        self.field_path = field_path
        self.raw_value = raw_value


@dataclass(frozen=True, slots=True)
class HalloyGeneral:
    background: RGBA
    border: RGBA
    horizontal_rule: RGBA
    unread_indicator: RGBA


@dataclass(frozen=True, slots=True)
class HalloyText:
    primary: RGBA
    secondary: RGBA
    tertiary: RGBA
    success: RGBA
    error: RGBA


@dataclass(frozen=True, slots=True)
class HalloyBufferServerMessages:
    default: RGBA
    extras: Mapping[str, RGBA] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HalloyBuffer:
    action: RGBA
    background: RGBA
    background_text_input: RGBA
    background_title_bar: RGBA
    border: RGBA
    border_selected: RGBA
    code: RGBA
    highlight: RGBA
    nickname: RGBA
    selection: RGBA
    timestamp: RGBA
    topic: RGBA
    url: RGBA
    server_messages: HalloyBufferServerMessages


@dataclass(frozen=True, slots=True)
class HalloyButtons:
    primaries: Mapping[str, Mapping[str, RGBA]] = field(default_factory=dict)
    secondaries: Mapping[str, Mapping[str, RGBA]] = field(default_factory=dict)

    @property
    def primary(self) -> Mapping[str, RGBA]:
        first = next(iter(self.primaries.values()), {})
        return first

    @property
    def secondary(self) -> Mapping[str, RGBA]:
        first = next(iter(self.secondaries.values()), {})
        return first


@dataclass(frozen=True, slots=True)
class HalloyTheme:
    source_name: str
    schema_version: str
    general: HalloyGeneral
    text: HalloyText
    buffer: HalloyBuffer
    buttons: HalloyButtons
    extra_top_sections: Mapping[str, object] = field(default_factory=dict)


_GENERAL_KEYS: tuple[str, ...] = (
    "background",
    "border",
    "horizontal_rule",
    "unread_indicator",
)

_TEXT_KEYS: tuple[str, ...] = (
    "primary",
    "secondary",
    "tertiary",
    "success",
    "error",
)

_BUFFER_KEYS: tuple[str, ...] = (
    "action",
    "background",
    "background_text_input",
    "background_title_bar",
    "border",
    "border_selected",
    "code",
    "highlight",
    "nickname",
    "selection",
    "timestamp",
    "topic",
    "url",
)

_BUTTON_KEYS: tuple[str, ...] = (
    "background",
    "background_hover",
    "background_selected",
    "background_selected_hover",
)


def _parse_color(
    value: object,
    *,
    field_path: str,
    source_name: str,
) -> RGBA:
    if not isinstance(value, str):
        raise ThemeColorError(
            f"expected color string, got {type(value).__name__}",
            source=source_name,
            field_path=field_path,
            raw_value=repr(value),
        )
    try:
        return from_hex(value)
    except (TypeError, ValueError) as exc:
        raise ThemeColorError(
            str(exc),
            source=source_name,
            field_path=field_path,
            raw_value=value,
        ) from exc


def _require_table(section: object, *, field_path: str, source_name: str) -> dict:
    if not isinstance(section, dict):
        raise ThemeSchemaError(
            f"expected TOML table, got {type(section).__name__}",
            source=source_name,
            field_path=field_path,
        )
    return section


def _require_color_field(
    table: Mapping[str, object],
    key: str,
    *,
    field_path: str,
    source_name: str,
) -> RGBA:
    if key not in table:
        raise ThemeSchemaError(
            f"missing required field {key!r}",
            source=source_name,
            field_path=field_path,
        )
    raw = table[key]
    sub_path = f"{field_path}.{key}"
    return _parse_color(raw, field_path=sub_path, source_name=source_name)


def _parse_general(loaded: Mapping[str, object], *, source_name: str) -> HalloyGeneral:
    base = "general"
    if base not in loaded:
        raise ThemeSchemaError(
            f"missing required section {base!r}",
            source=source_name,
            field_path=base,
        )
    section = _require_table(loaded[base], field_path=base, source_name=source_name)
    parsed = {
        key: _require_color_field(section, key, field_path=base, source_name=source_name)
        for key in _GENERAL_KEYS
    }
    return HalloyGeneral(**parsed)


def _parse_text(loaded: Mapping[str, object], *, source_name: str) -> HalloyText:
    base = "text"
    if base not in loaded:
        raise ThemeSchemaError(
            f"missing required section {base!r}",
            source=source_name,
            field_path=base,
        )
    section = _require_table(loaded[base], field_path=base, source_name=source_name)
    parsed = {
        key: _require_color_field(section, key, field_path=base, source_name=source_name)
        for key in _TEXT_KEYS
    }
    return HalloyText(**parsed)


def _parse_buffer_server_messages(
    table: object,
    *,
    field_path: str,
    source_name: str,
) -> HalloyBufferServerMessages:
    section = _require_table(table, field_path=field_path, source_name=source_name)
    if "default" not in section:
        raise ThemeSchemaError(
            "missing required field 'default'",
            source=source_name,
            field_path=field_path,
        )
    default = _parse_color(
        section["default"],
        field_path=f"{field_path}.default",
        source_name=source_name,
    )
    extras: dict[str, RGBA] = {}
    for key, value in section.items():
        if key == "default":
            continue
        sub_path = f"{field_path}.{key}"
        if isinstance(value, (dict, list)):
            continue
        try:
            extras[key] = _parse_color(value, field_path=sub_path, source_name=source_name)
        except ThemeColorError:
            continue
    return HalloyBufferServerMessages(default=default, extras=extras)


def _parse_buffer(loaded: Mapping[str, object], *, source_name: str) -> HalloyBuffer:
    base = "buffer"
    if base not in loaded:
        raise ThemeSchemaError(
            f"missing required section {base!r}",
            source=source_name,
            field_path=base,
        )
    section = _require_table(loaded[base], field_path=base, source_name=source_name)
    color_fields = {
        key: _require_color_field(section, key, field_path=base, source_name=source_name)
        for key in _BUFFER_KEYS
    }
    sm = section.get("server_messages")
    if sm is None:
        raise ThemeSchemaError(
            "missing required section 'buffer.server_messages'",
            source=source_name,
            field_path=f"{base}.server_messages",
        )
    server_messages = _parse_buffer_server_messages(
        sm,
        field_path=f"{base}.server_messages",
        source_name=source_name,
    )
    return HalloyBuffer(server_messages=server_messages, **color_fields)


def _parse_button_subsection(
    section: object,
    *,
    field_path: str,
    source_name: str,
) -> Mapping[str, RGBA]:
    table = _require_table(section, field_path=field_path, source_name=source_name)
    parsed: dict[str, RGBA] = {}
    for key in _BUTTON_KEYS:
        if key not in table:
            raise ThemeSchemaError(
                f"missing required field {key!r}",
                source=source_name,
                field_path=field_path,
            )
        parsed[key] = _require_color_field(
            table,
            key,
            field_path=field_path,
            source_name=source_name,
        )
    return parsed


def _parse_buttons(loaded: Mapping[str, object], *, source_name: str) -> HalloyButtons:
    base = "buttons"
    if base not in loaded:
        raise ThemeSchemaError(
            f"missing required section {base!r}",
            source=source_name,
            field_path=base,
        )
    section = _require_table(loaded[base], field_path=base, source_name=source_name)
    primaries: dict[str, Mapping[str, RGBA]] = {}
    secondaries: dict[str, Mapping[str, RGBA]] = {}
    for kind, target in (("primary", primaries), ("secondary", secondaries)):
        if kind not in section:
            raise ThemeSchemaError(
                f"missing required section '{base}.{kind}'",
                source=source_name,
                field_path=f"{base}.{kind}",
            )
        kind_table = section[kind]
        if not isinstance(kind_table, dict):
            raise ThemeSchemaError(
                f"expected TOML table, got {type(kind_table).__name__}",
                source=source_name,
                field_path=f"{base}.{kind}",
            )
        target[kind] = _parse_button_subsection(
            kind_table,
            field_path=f"{base}.{kind}",
            source_name=source_name,
        )
    return HalloyButtons(primaries=primaries, secondaries=secondaries)


def _load_toml(data: bytes, *, source_name: str) -> dict:
    if not data.strip():
        raise ThemeParseError("empty theme content", source=source_name)
    try:
        loaded = tomllib.loads(data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ThemeParseError(
            f"theme is not valid UTF-8: {exc}",
            source=source_name,
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise ThemeParseError(
            f"invalid TOML: {exc}",
            source=source_name,
        ) from exc
    if not isinstance(loaded, dict):
        raise ThemeParseError(
            f"top-level must be a table, got {type(loaded).__name__}",
            source=source_name,
        )
    return loaded


def parse_halloy_theme_bytes(data: bytes, *, source_name: str) -> HalloyTheme:
    loaded = _load_toml(data, source_name=source_name)

    general = _parse_general(loaded, source_name=source_name)
    text = _parse_text(loaded, source_name=source_name)
    buffer = _parse_buffer(loaded, source_name=source_name)
    buttons = _parse_buttons(loaded, source_name=source_name)

    known = {"general", "text", "buffer", "buttons"}
    extras = {k: v for k, v in loaded.items() if k not in known}

    return HalloyTheme(
        source_name=source_name,
        schema_version=SCHEMA_VERSION,
        general=general,
        text=text,
        buffer=buffer,
        buttons=buttons,
        extra_top_sections=extras,
    )


def parse_halloy_theme(source: str | Path | IO[bytes] | bytes) -> HalloyTheme:
    if isinstance(source, bytes):
        return parse_halloy_theme_bytes(source, source_name="<bytes>")
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.is_file():
            raise ThemeParseError(
                f"theme path is not a regular file: {path}",
                source=str(path),
            )
        return parse_halloy_theme_bytes(path.read_bytes(), source_name=path.name)
    if hasattr(source, "read"):
        data = source.read()
        if not isinstance(data, bytes):
            data = data.encode("utf-8")
        name = getattr(source, "name", "<stream>")
        if isinstance(name, str):
            stem = Path(name).name
        else:
            stem = "<stream>"
        return parse_halloy_theme_bytes(data, source_name=stem)
    raise TypeError(f"unsupported source type: {type(source).__name__}")


__all__ = [
    "HalloyBuffer",
    "HalloyBufferServerMessages",
    "HalloyButtons",
    "HalloyGeneral",
    "HalloyText",
    "HalloyTheme",
    "SCHEMA_VERSION",
    "ThemeColorError",
    "ThemeParseError",
    "ThemeSchemaError",
    "parse_halloy_theme",
    "parse_halloy_theme_bytes",
]
