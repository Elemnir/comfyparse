import copy


class ConfigSpecError(Exception):
    pass


class ValidationError(Exception):
    pass


class Namespace:
    def __init__(self, name=None, **kwargs):
        self.attrs = dict(kwargs)
        self.name = name

    def __getattr__(self, name):
        try:
            return self.attrs[name]
        except KeyError as exc:
            raise AttributeError("Namespace {} has no attribute: {}".format(
                self.name if self.name else "<unnamed>", name
            )) from exc

    def __setattr__(self, name, value):
        self.attrs[name] = value

    def __contains__(self, key):
        return key in self.attrs

    def __getitem__(self, index):
        return self.attrs[index]

    def __iter__(self):
        return self.attrs.__iter__()

    def get(self, key, default=None):
        return self.attrs.get(key, default)


class ConfigSetting:
    def __init__(self, name, desc="", required=False, default=None, choices=None, convert=None, validate=None):
        self.name = name
        self.desc = desc
        self.required = required
        self.default = default
        self.choices = choices
        self.convert = convert
        self.validate = validate

    def validate_value(self, raw_value=None):
        if self.required and raw_value is None:
            raise ValidationError(f"Missing required setting: {self.name}")

        if raw_value is not None:
            value = self.convert(raw_value) if self.convert else raw_value
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
    def __init__(self, kind, named=False, desc="", required=False, validate=None):
        self.kind = kind
        self.named = named
        self.desc = desc
        self.required = required
        self.validate = validate
        self.settings = {}
        self.children = {}

    def add_block(self, kind, named=False, desc="", required=False, validate=None):
        if kind in self.settings or kind in self.children:
            raise ConfigSpecError(f"Duplicate use of setting name or block kind: {kind}")
        self.children[kind] = ConfigBlock(kind, named, desc, required, validate)
        return self.children[kind]

    def add_setting(self, name, desc="", required=False, default=None, choices=None, convert=None, validate=None):
        if name in self.children:
            raise ConfigSpecError(f"Duplicate use of setting name or block kind: {name}")
        self.settings[name] = ConfigSetting(
            name, desc, required, default, choices, convert, validate
        )

    def validate_block(self, block: Namespace):
        validated = copy.deepcopy(block)
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
