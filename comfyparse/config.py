"""
    comfyparse.config
    -----------------

    This module provides the classes for defining the schema, validating
    inputs, and creating the resulting namespace for a configuration.
"""
from collections.abc import Callable, Sequence
import textwrap
from typing import Any, Optional, Union


RST_REQUIRED = "**Required**"
RST_SECTIONS = "=-`:.'\"~^_*+#"


class ConfigSpecError(Exception):
    """Raised when an error occurs while adding a new setting or block."""


class ValidationError(Exception):
    """Raised when a block or setting's value fail to validate."""


class Namespace:
    """A dict wrapper for allowing both indexing-based and attribute-based access to
    contents.

    :param name: An optional name to help identify the namespace.
    :param **kwargs: All keyword arguments are treated as entries in the
        internally-managed dictionary.
    """
    def __init__(self, name: Optional[str] = None, **kwargs):
        self._attrs = dict(kwargs)
        self._name = name
        self._repr_name = "Namespace" + (f"[{name}]" if name else "")

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_") or name not in self._attrs:
            raise AttributeError(f"{self._repr_name} has no attribute '{name}'")
        return self._attrs[name]

    def __contains__(self, key: str) -> bool:
        return key in self._attrs

    def __getitem__(self, index: str) -> Any:
        return self._attrs[index]

    def __setitem__(self, name: str, value: Any) -> None:
        self._attrs[name] = value

    def __iter__(self):
        return self._attrs.__iter__()

    def __str__(self):
        contents = [ f"{k}: {v}" for k, v in self._attrs.items() ]
        return f"{self._repr_name}{{" + ", ".join(contents) + "}"

    def copy(self) -> 'Namespace':
        """Return a new Namespace which is a copy of this one."""
        return Namespace(name=self._name, **self._attrs)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Return the given key if it exists within this Namespace, otherwise return the
        value of ``default``.
        """
        return self._attrs.get(key, default)


class ConfigSetting:
    """Defines the specification for a single configuration setting.

    :param name: The name of this setting.
    :param desc: A description of the setting. Included in automatic documentation.
    :param required: Whether the setting may be omitted. (Default ``False``)
    :param default: A value to use when the setting is omitted from a configuration.
    :param choices: Optionally, a list of allowed values for the setting.
    :param convert: Optionally, a callable which accepts the raw parsed value and returns
        an object of the appropriate type.
    :param validate: Optionally, a callable which accepts the (potentially converted)
        value and returns whether or not it is a valid value for the setting.
    """
    def __init__(
            self, name: str, desc: str = "", required: bool = False,
            default: Optional[Any] = None, choices: Optional[Sequence] = None,
            convert: Optional[Callable[[Union[list, str]], Any]] = None,
            validate: Optional[Callable[[Any], bool]] = None):
        self.name = name
        self.desc = desc
        self.required = required
        self.default = default
        self.choices = choices
        self.convert = convert
        self.validate = validate

    def render_as_table_row(self, name_width: int, default_width: int) -> str:
        """Renders the setting's parameters as a string for inclusion in the
        table generated by ``ConfigBlock.generate_docs()`` which contains this
        setting.
        """
        initial = "\n" + self.name.ljust(name_width+1)
        initial += (str(self.default) if not self.required else RST_REQUIRED).ljust(default_width+1)
        if not self.desc and not self.choices:
            return initial
        return textwrap.fill(
            str(self.desc) + (f"\n(Choices: {self.choices})" if self.choices else ""),
            width = max(90, name_width + default_width + 52),
            initial_indent = initial,
            subsequent_indent = " " * (name_width + default_width + 2),
        )

    def validate_value(self, raw_value: Optional[str] = None) -> Any:
        """Returns a validated and optionally converted value from a raw value (or None)"""
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

        if self.validate is not None and not self.validate(value):
            raise ValidationError(
                f"Validation check failed for setting {self.name}={raw_value}"
            )

        return value


class ConfigBlock:
    """Defines a configuration block. 

    :param kind: The identifier for the block.
    :param named: If ``True``, multiple instances of a block can be included at the global
        configuration level. Each instance must include an additional name identifier to
        distinguish them. (Default ``False``)
    :param desc: A description of the block. Included in automatic documentation.
    :param required: Whether the block may be omitted. (Default ``False``)
    :param validate: Optionally, a callable which accepts the block after each field has
        been validated and returns whether or not is is valid.
    """
    def __init__(
            self, kind: str, named: bool = False, desc: str = "", required: bool = False,
            validate: Optional[Callable[[Namespace], bool]] = None):
        self.kind = kind
        self.named = named
        self.desc = desc
        self.required = required
        self.validate = validate
        self.settings: dict[str, ConfigSetting] = {}
        self.children: dict[str, 'ConfigBlock'] = {}

    def add_block(
            self, kind: str, named: bool = False, desc: str = "", required: bool = False,
            validate: Optional[Callable[[Namespace], bool]] = None) -> 'ConfigBlock':
        """Define and return a new configuration block nested within this block. 

        :param kind: The identifier for the block.
        :param named: If ``True``, multiple instances of a block can be included at the
            global configuration level. Each instance must include an additional name
            identifier to distinguish them. (Default ``False``)
        :param desc: A description of the block. Included in automatic documentation.
        :param required: Whether the block may be omitted. (Default ``False``)
        :param validate: Optionally, a callable which accepts the block after each field
        has been validated and returns whether or not is is valid.

        :raise comfyparse.config.ConfigSpecError: Raised if the kind identifier is already
            in use within this block.

        :return: The newly defined block.
        :rtype: ConfigBlock

        The returned configuration block similarly supports the ``add_setting`` and 
        ``add_block`` methods to allow for hierarchical configuration construction.
        """
        if kind in self.settings or kind in self.children:
            raise ConfigSpecError(f"Duplicate use of setting name or block kind: {kind}")
        self.children[kind] = ConfigBlock(kind, named, desc, required, validate)
        return self.children[kind]

    def add_setting(
            self, name: str, desc: str = "", required: bool = False,
            default: Optional[Any] = None, choices: Optional[Sequence] = None,
            convert: Optional[Callable[[Union[list, str]], Any]] = None,
            validate: Optional[Callable[[Any], bool]] = None) -> None:
        """Define a new configuration setting within this block.

        :param name: The name of this setting.
        :param desc: A description of the setting. Included in automatic documentation.
        :param required: Whether the setting may be omitted. (Default ``False``)
        :param default: A value to use when the setting is omitted from a configuration.
        :param choices: Optionally, a list of allowed values for the setting.
        :param convert: Optionally, a callable which accepts the raw parsed value and
            returns an object of the appropriate type.
        :param validate: Optionally, a callable which accepts the (potentially converted)
            value and returns whether or not it is a valid value for the setting.

        :raise comfyparse.config.ConfigSpecError: Raised if the name is already in use
            within this block.
        """

        if name in self.settings or name in self.children:
            raise ConfigSpecError(f"Duplicate use of setting name or block kind: {name}")
        if required and default is not None:
            raise ConfigSpecError(f"Required setting '{name}' shouldn't provide a default")
        self.settings[name] = ConfigSetting(
            name, desc, required, default, choices, convert, validate
        )

    def generate_docs(self, level: int=0) -> str:
        """Returns a reStructuredText string containing documentation for this
        block and its settings, as well as the documentation of its child blocks.
        """
        rval = self.kind + "\n" + (RST_SECTIONS[level % len(RST_SECTIONS)] * 10) + "\n\n" + self.desc
        if self.required and level > 0:
            rval += f"\n\nA ``{self.kind}`` block is required."
        if self.named:
            rval += f"\n\nMultiple ``{self.kind}`` blocks can be defined and must"
            rval += " include a name to distinguish them."
        if self.settings:
            rval += "\n\nIt supports the following settings:\n\n"
            lname, ldefault = self._get_doc_field_widths()
            rval += ("=" * lname) + " " + ("=" * ldefault) + " ===========\n"
            rval += "Name".center(lname) + " " + "Required/".center(ldefault) + " Description\n"
            rval += (" " * lname) + " " + "Default".center(ldefault) + "\n"
            rval += ("=" * lname) + " " + ("=" * ldefault) + " ==========="
            for setting in sorted(self.settings.values(), key=lambda x: not x.required):
                rval += setting.render_as_table_row(lname, ldefault)
            rval += "\n" + ("=" * lname) + " " + ("=" * ldefault) + " ===========\n"
        if self.children:
            rval += "\nThe following subblocks are required/supported:\n\n"
            for block in sorted(self.children.values(), key=lambda x: not x.required):
                rval += block.generate_docs(level+1) 
        return rval

    def _get_doc_field_widths(self):
        """Return the longest name and default string lengths for table generation."""
        lname, ldefault = 0, len(RST_REQUIRED)
        for setting in self.settings.values():
            if (lenname := len(str(setting.name))) > lname:
                lname = lenname
            if (lendef := len(str(setting.default))) > ldefault:
                ldefault = lendef
        return lname, ldefault

    def validate_block(self, block: Namespace) -> Namespace:
        """Returns a validated copy of the given block with all child blocks and settings
        validated. Settings values in the returned Namespace will also have been converted
        if a ``convert`` callable was defined for them.
        """
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
            if kind not in block:
                if child.required:
                    raise ValidationError(f"Missing required block: {kind}")
                continue
            if isinstance(block[kind], dict):
                for key in block[kind]:
                    validated[kind][key] = child.validate_block(block[kind][key])
            else:
                validated[kind] = child.validate_block(block[kind])

        if self.validate is not None and not self.validate(validated):
            raise ValidationError(f"Validation check failed for block {self.kind}")

        return validated
