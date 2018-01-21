"""
    See smart_json_class.py for usage.
"""
from enum import Enum, auto


class NamedProperty(property):
    def __init__(self, name, fget=None, fset=None, fdel=None):
        super().__init__(fget, fset, fdel)
        self._name = name

    @property
    def name(self):
        return self._name


class JsonStringFormat(Enum):
    """ see https://spacetelescope.github.io/understanding-json-schema/reference/string.html#format """
    date_time = auto()
    email = auto()
    hostname = auto()
    ipv4 = auto()
    ipv6 = auto()
    uri = auto()


class Field(object):
    """ A single field class, holds information regarding python type checking and json-serialization """

    def __init__(self, field_type, description=None, json_format: JsonStringFormat=None, min_value=None, max_value=None,
                 pattern=None, enum=None):
        """
        :param field_type: The python type of the field, must be provided.
        :param description: The description of the field (would be displayed in the GUI)
        :param json_format: if provided, will be returned as format json-field
        :param min_value: if provided, will be returned as format json-field
        :param max_value: if provided, will be returned as format json-field
        :param pattern: if provided, will be returned as format json-field
        :param enum: if provided, will be checked that the values are valid and will be returned as format json-field
        """
        self._type = field_type
        self._description = description
        self._name = None
        if json_format is not None:
            assert isinstance(json_format, JsonStringFormat)
        self._format = json_format
        if min_value is not None:
            assert isinstance(min_value, int)
        self._min = min_value
        if max_value is not None:
            assert isinstance(max_value, int)
        self._max = max_value
        if pattern is not None:
            assert isinstance(pattern, str)
        self._pattern = pattern
        if enum is not None:
            assert isinstance(enum, list)
        self._enum = enum

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def type(self):
        return self._type

    @property
    def format(self):
        return self._format

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def pattern(self):
        return self._pattern

    @property
    def enum(self):
        return self._enum

    @property
    def json_name(self):
        if issubclass(self.type, int):
            return 'number'
        elif issubclass(self.type, str):
            return 'string'
        elif issubclass(self.type, bool):
            return 'boolean'
        return 'string'

    def __repr__(self):
        return f'<{self.__class__.__name__} \'{self._name}\' {self._type}>'

    def __eq__(self, other):
        assert isinstance(other, str)
        return self._name == other

    def _set_name(self, name: str):
        assert isinstance(name, str)
        self._name = name

    def get_field(self, name: str):
        """ returns a new python property instance with both getter and setter for the current field that will get
            installed on a SmartJsonClass derived class. """
        from axonius.smart_json_class import SmartJsonClass
        self._set_name(name)
        field_type = self._type
        field_instance = self
        is_smart_field = issubclass(field_type, SmartJsonClass)

        def getter(self: SmartJsonClass):
            """
            Setter for fields on the SmartJsonClass
            :param self: SmartJsonClass instance
            :return the value of the current property
            """
            return self._dict[name]

        def setter(self: SmartJsonClass, value):
            """
            Setter for fields on the SmartJsonClass
            :param self: SmartJsonClass instance
            :param value: The new value for the current property
            """
            # Type-check for value before setting inside the dict of SmartJsonClass
            if is_smart_field and isinstance(value, dict):  # accept also free-dict instead of SmartJsonClass
                pass
            elif value is not None:
                if not isinstance(value, field_type):
                    raise TypeError(f'{name} expected to be {field_type}, got {value} of {type(value)} instead')
                if field_instance._enum:
                    if value not in field_instance._enum:
                        raise ValueError(f'Unexpected enum value {value}, '
                                         f'expected one of {field_instance.enum} values')
                if field_instance._min and value < field_instance._min:
                    raise ValueError(f'Got {value} less then defined minimum {field_instance.min}')
                if field_instance._max and value > field_instance._max:
                    raise ValueError(f'Got {value} more then defined maximum {field_instance.max}')
            elif name not in self._dict:
                return
            self._dict[name] = value
            self._extend_names(name, value)  # add our name to the SmartJsonClass instance

        getter.__name__ = name
        setter.__name__ = name
        field = NamedProperty(name, getter, setter)
        return field


class ListField(Field):
    """ A single field class, holds information regarding python type checking and json-serialization
        for a list-field
    """

    def get_field(self, name: str):
        """ returns a new python property instance with both getter and setter for the current field list that will get
            installed on a SmartJsonClass derived class. """
        from axonius.smart_json_class import SmartJsonClass
        self._set_name(name)
        field_type = self._type
        is_smart_field = issubclass(field_type, SmartJsonClass)

        # define a new specific type-checking list class
        class _List(list):
            def append(self, obj):
                if is_smart_field and isinstance(obj, dict):  # accept also free-dict instead of SmartJsonClass
                    pass
                elif not isinstance(obj, field_type):
                    raise TypeError(f'{name} expected to be {field_type}, got {obj} of {type(obj)} instead')
                super(_List, self).append(obj)

        def getter(self: SmartJsonClass):
            """
            Setter for fields on the SmartJsonClass
            :param self: SmartJsonClass instance
            :return the value of the current property
            """
            if name not in self._dict:
                self._dict[name] = _List()  # creates a new instance of type-checking list for this type
            return self._dict[name]

        def setter(self: SmartJsonClass, value):
            """
            Setter for fields on the SmartJsonClass
            :param self: SmartJsonClass instance
            :param value: The new value for the current property
            """
            # Type-check for value before setting inside the dict of SmartJsonClass
            if value is not None:
                if not isinstance(value, list):
                    raise TypeError(f'{name} expected to be list of {field_type}, got {value} of {type(value)} instead')

                for item in value:
                    if is_smart_field and isinstance(item, dict):  # accept also free-dict instead of SmartJsonClass
                        pass
                    elif not isinstance(item, field_type):
                        raise TypeError(f'{name} expected to be {field_type}, got {item} of {type(item)} instead')
            elif name not in self._dict:
                return
            self._dict[name] = _List(value)  # set new (type-checked-list) value inside the dict of SmartJsonClass
            self._extend_names(name, value)  # add our name to the SmartJsonClass instance

        getter.__name__ = name
        setter.__name__ = name
        field = NamedProperty(name, getter, setter)
        return field
