"""
    See smart_json_class.py for usage.
"""
from enum import Enum, auto
import datetime


class NamedProperty(property):
    def __init__(self, name, fget=None, fset=None, fdel=None):
        super().__init__(fget, fset, fdel)
        self._name = name

    @property
    def name(self):
        return self._name


class JsonFormat(Enum):
    """ pass """


class JsonStringFormat(JsonFormat):
    """ see https://spacetelescope.github.io/understanding-json-schema/reference/string.html#format """
    date_time = auto()
    date = auto()
    time = auto()
    email = auto()
    hostname = auto()
    ip = auto()
    ipv4 = auto()
    ipv6 = auto()
    uri = auto()
    image = auto()
    associated_device = auto()
    subnet = auto()


class JsonNumericFormat(JsonFormat):
    percentage = auto()


class JsonArrayFormat(JsonFormat):
    table = auto()
    calendar = auto()


class Field(object):
    """ A single field class, holds information regarding python type checking and json-serialization """

    def __init__(self, field_type, title=None, description=None, converter=None, json_format: JsonFormat = None,
                 min_value=None, max_value=None, pattern=None, enum=None):
        """
        :param field_type: The python type of the field, must be provided.
        :param description: The description of the field (would be displayed in the GUI)
        :param converter: if provided, will be used to convert the function supplied to a standard form
        :param json_format: if provided, will be returned as format json-field
        :param min_value: if provided, will be returned as format json-field
        :param max_value: if provided, will be returned as format json-field
        :param pattern: if provided, will be returned as format json-field
        :param enum: if provided, will be checked that the values are valid and will be returned as format json-field
        """
        self._type = field_type
        self._title = title
        self._description = description
        if converter is not None:
            assert callable(converter)
        self._converter = converter
        self._name = None
        if json_format is None and isinstance(field_type, type) and issubclass(field_type, datetime.datetime):
            json_format = JsonStringFormat.date_time
        if json_format is not None:
            assert isinstance(json_format, JsonFormat)
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
            assert isinstance(enum, list) or issubclass(enum, Enum)
            assert len(set(map(lambda item: item.lower() if isinstance(item, str) else item, enum))) == len(enum)
        elif issubclass(field_type, Enum):
            enum = field_type
        self._enum = enum
        self._dynamic = False

    @property
    def name(self):
        return self._name

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    @property
    def converter(self):
        return self._converter

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
    def dynamic(self):
        return self._dynamic

    @property
    def json_name(self):
        if issubclass(self.type, bool):
            return 'bool'
        elif issubclass(self.type, int):
            return 'integer'
        elif issubclass(self.type, float):
            return 'number'
        elif issubclass(self.type, str):
            return 'string'
        elif issubclass(self.type, dict):
            return 'object'
        return 'string'

    def __repr__(self):
        return f'<{self.__class__.__name__} \'{self._name}\' {self._type}>'

    def __eq__(self, other):
        assert isinstance(other, str)
        return self._name == other

    def set_dynamic(self, val: bool):
        assert isinstance(val, bool)
        self._dynamic = val

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

            # There are some special cases, where we consider the value as none.
            # If we expect str and we get '', or if we expect str and we get 0 (int).
            if (field_type == str and isinstance(value, str) and value == '') \
                    or (field_type == str and isinstance(value, int) and value == 0):
                value = None

            if value is not None:
                # If we expect an str, but we get a list with one str value, just take this value.
                if isinstance(value, list) and len(value) == 1 and field_type == str and isinstance(value[0], str):
                    value = value[0]

                # We want to avoid stupid int/str/float mistakes. so lets try converting these values first.
                # This means, that if we expect an str but get something else, it will be auto-converted.
                if not isinstance(value, field_type) and (field_type == str or field_type == int or field_type == float):
                    try:
                        value = field_type(value)
                    except Exception:
                        pass

                # If still its not...
                if not isinstance(value, field_type):
                    raise TypeError(f'{name} expected to be {field_type}, got {value} of {type(value)} instead')

                if field_instance._enum:
                    for item in field_instance._enum:
                        if isinstance(value, str) and isinstance(item, str) and value.lower() == item.lower():
                            value = item
                            break
                        elif value == item:
                            value = item
                            break
                    else:
                        raise ValueError(f'Unexpected enum value {value}, '
                                         f'expected one of {field_instance.enum} values')
                if field_instance._min and value < field_instance._min:
                    raise ValueError(f'Got {value} less then defined minimum {field_instance.min}')
                if field_instance._max and value > field_instance._max:
                    raise ValueError(f'Got {value} more then defined maximum {field_instance.max}')
            else:
                if name in self._dict:
                    self._dict.pop(name)
                return

            if field_instance.converter:
                value = field_instance.converter(value)

            # Again, after converter.
            if value is None or (isinstance(value, str) and value == ''):
                if name in self._dict:
                    self._dict.pop(name)
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
        field_instance = self
        is_smart_field = issubclass(field_type, SmartJsonClass)

        # define a new specific type-checking list class
        class _List(list):
            def append(self, obj):
                if is_smart_field and isinstance(obj, dict):  # accept also free-dict instead of SmartJsonClass
                    pass
                elif not isinstance(obj, field_type):
                    raise TypeError(f'{name} expected to be {field_type}, got {obj} of {type(obj)} instead')
                if field_instance.converter:
                    obj = field_instance.converter(obj)
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
            else:
                if name in self._dict:
                    self._dict.pop(name)
                return

            if field_instance.converter:
                new_list = []
                for item in value:
                    new_list.append(field_instance.converter(item))
                value = new_list
            self._dict[name] = _List(value)  # set new (type-checked-list) value inside the dict of SmartJsonClass
            self._extend_names(name, value)  # add our name to the SmartJsonClass instance

        getter.__name__ = name
        setter.__name__ = name
        field = NamedProperty(name, getter, setter)
        return field
