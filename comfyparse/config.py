from collections.abc import Callable, Sequence
from typing import Any, Optional, Union

class ConfigSpecError(Exception):
    pass


class ValidationError(Exception):
    pass


class Namespace:
    def __init__(self, name: Optional[str] = None, **kwargs):
        self._attrs = dict(kwargs)
        self.name = name if name else "<unnamed>"

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_") or name not in self._attrs:
            raise AttributeError(f"Namespace {self.name} has no attribute '{name}'")
        return self._attrs[name]

    def __contains__(self, key: str) -> bool:
        return key in self._attrs

    def __getitem__(self, index: str) -> Any:
        return self._attrs[index]

    def __setitem__(self, name: str, value: Any) -> None:
        self._attrs[name] = value

    def __iter__(self):
        return self._attrs.__iter__()

    def copy(self) -> 'Namespace':
        return Namespace(name=self.name, **self._attrs)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self._attrs.get(key, default)


class ConfigSetting:
    def __init__(
            self, name: str, desc: str = "", required: bool = False,
            default: Optional[Any] = None, choices: Optional[Sequence] = None,
            convert: Optional[Callable[[Union[list, str]], Any]] = None,
            validate: Optional[Callable[[Any], None]] = None):
        self.name = name
        self.desc = desc
        self.required = required
        self.default = default
        self.choices = choices
        self.convert = convert
        self.validate = validate

    def validate_value(self, raw_value: Optional[str] = None) -> Any:
        if self.required and raw_value is None:
            raise ValidationError(f"Missing required setting: {self.name}")

        if raw_value is not None:
            try:
                value = self.convert(raw_value) if self.convert else raw_value
            except Exception as exc:
                raise ValidationError(
                    f"Error on setting '{self.name}' with value '{raw_value}'"
                ) from exc
        else:
            value = self.default

        if self.choices and value not in self.choices:
            raise ValidationError(
                f"Invalid setting {self.name}={raw_value}, choices are {self.choices}"
            )

        if self.validate is not None:
            self.validate(value)

        return value


class ConfigBlock:
    def __init__(
            self, kind: str, named: bool = False, desc: str = "", required: bool = False,
            validate: Optional[Callable[[Namespace], None]] = None):
        self.kind = kind
        self.named = named
        self.desc = desc
        self.required = required
        self.validate = validate
        self.settings: dict[str, ConfigSetting] = {}
        self.children: dict[str, 'ConfigBlock'] = {}

    def add_block(
            self, kind: str, named: bool = False, desc: str = "", required: bool = False,
            validate: Optional[Callable[[Namespace], None]] = None) -> 'ConfigBlock':
        if kind in self.settings or kind in self.children:
            raise ConfigSpecError(f"Duplicate use of setting name or block kind: {kind}")
        self.children[kind] = ConfigBlock(kind, named, desc, required, validate)
        return self.children[kind]

    def add_setting(
            self, name: str, desc: str = "", required: bool = False,
            default: Optional[Any] = None, choices: Optional[Sequence] = None,
            convert: Optional[Callable[[Union[list, str]], Any]] = None,
            validate: Optional[Callable[[Any], None]] = None) -> None:
        if name in self.settings or name in self.children:
            raise ConfigSpecError(f"Duplicate use of setting name or block kind: {name}")
        self.settings[name] = ConfigSetting(
            name, desc, required, default, choices, convert, validate
        )

    def validate_block(self, block: Namespace) -> Namespace:
        validated = block.copy()
        for key in block:
            if key not in self.settings and key not in self.children:
                raise ValidationError(f"Unrecognized setting or block kind: {key}")
            if key in self.settings and isinstance(block[key], Namespace):
                raise ValidationError(f"Invalid block kind should be setting: {key}")
            if key in self.children:
                if not isinstance(block[key], (Namespace, dict)):
                    raise ValidationError(f"Invalid setting should be a block: {key}")

        for name, setting in self.settings.items():
            validated[name] = setting.validate_value(block.get(name, None))

        for kind, child in self.children.items():
            if kind not in block and child.required:
                raise ValidationError(f"Missing required block: {kind}")
            if isinstance(block[kind], dict):
                for key in block[kind]:
                    validated[kind][key] = child.validate_block(block[kind][key])
            else:
                validated[kind] = child.validate_block(block[kind])

        if self.validate is not None:
            self.validate(validated)

        return validated
