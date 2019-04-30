"""
    See smart_json_class.py for usage.
"""
from enum import Enum, auto
import datetime

# pylint: disable=too-many-branches,protected-access,too-many-instance-attributes


def compare_enum_by_name(value1, value2):
    if isinstance(value1, Enum):
        value1 = value1.name

    if isinstance(value2, Enum):
        value2 = value2.name

    if all([isinstance(value, (str, bytes)) for value in [value1, value2]]):
        return value1.lower() == value2.lower()
    return False


def compare_enum_by_value(value1, value2):
    if isinstance(value1, Enum):
        value1 = value1.value

    if isinstance(value2, Enum):
        value2 = value2.value

    return value1 == value2


def compare_enum(value1, value2):
    """ case insensitive compare 2 values, each value can be either string int or enum,
        if value is enum use the enum name to compare.
        if failed try to compare by value
        if nothing work fallback to regular compare"""

    if compare_enum_by_name(value1, value2):
        return True

    if compare_enum_by_value(value1, value2):
        return True

    return value1 == value2


def prepare_value(value, field_type, field_instance, name):
    enum = field_instance.enum

    # We must import SmartJsonClass in the middle of the function because of bi-directional dependencies
    from axonius.smart_json_class import SmartJsonClass

    if value is None:
        raise TypeError(f'{name} expected to be {field_type}, got {value} of {type(value)} instead')

    # If we expect an str, but we get a list with one str value, just take this value.
    if isinstance(value, list) and len(value) == 1 and field_type == str and isinstance(value[0], str):
        value = value[0]

    if enum:
        values = [item for item in enum if compare_enum(item, value)]
        if not values:
            raise ValueError(f'Unexpected enum value {value}, '
                             f'expected one of {enum} values')
        value = values[0]

        # Enum in value or enum=Enum implies type is str
        if isinstance(value, Enum):
            value = value.name
            field_type = str

        if issubclass(field_type, Enum):
            field_type = str

    # We want to avoid stupid int/str/float mistakes. so lets try converting these values first.
    # This means, that if we expect an str but get something else, it will be auto-converted.
    if not isinstance(value, field_type) and field_type in [str, int, float]:
        try:
            value = field_type(value)
        except Exception:
            pass

    # If still its not...
    if not isinstance(value, field_type):
        # accept dict for SmartJsonClass
        if not (issubclass(field_type, SmartJsonClass) and isinstance(value, dict)):
            raise TypeError(f'{name} expected to be {field_type}, got {value} of {type(value)} instead')

    if field_instance.min and value < field_instance.min:
        raise ValueError(f'Got {value} less then defined minimum {field_instance.min}')
    if field_instance.max and value > field_instance.max:
        raise ValueError(f'Got {value} more then defined maximum {field_instance.max}')

    if field_instance.converter:
        value = field_instance.converter(value)

    return value


class FieldGetter:
    def __init__(self, field_instance, field_type, name):
        self.__name__ = name
        self.field_type = field_type
        self.field_instance = field_instance
        self.name = name

    def __call__(self, smart_json):
        """
        Getter for fields on the SmartJsonClass
        :param smart_json: SmartJsonClass instance
        :return the value of the current property
        """
        return smart_json._dict[self.name]

# define a new specific type-checking list class


class _List(list):
    def __init__(self, field_type, field_instance, name, *args, **kwargs):
        self.field_type = field_type
        self.field_instance = field_instance
        self.name = name
        super().__init__(*args, **kwargs)

    def append(self, obj):
        super(_List, self).append(prepare_value(obj, self.field_type, self.field_instance, self.name))


class ListGetter(FieldGetter):
    def __call__(self, smart_json):
        if self.name not in smart_json._dict:
            # creates a new instance of type-checking list for this type
            smart_json._dict[self.name] = _List(self.field_type, self.field_instance, self.name)
        return super().__call__(smart_json)


class FieldSetter:
    def __init__(self, field_instance, field_type, name):
        self.__name__ = name
        self.field_type = field_type
        self.field_instance = field_instance
        self.name = name

    def _prepare_value(self, value):
        if value is None:
            return None

        # There are some special cases, where we consider the value as none.
        # If we expect str and we get '', or if we expect str and we get 0 (int).
        if self.field_type == str and isinstance(value, (str, int)) and value in ('', 0):
            return None

        return prepare_value(value, self.field_type, self.field_instance, self.name)

    def __call__(self, smart_json, value):
        """
        Setter for fields on the SmartJsonClass
        :param self: SmartJsonClass instance
        :param value: The new value for the current property
        """
        value = self._prepare_value(value)

        if value is None:
            if self.name in smart_json._dict:
                smart_json._dict.pop(self.name)
            return

        smart_json._dict[self.name] = value
        smart_json._extend_names(self.name, value)  # add our name to the SmartJsonClass instance


class ListSetter(FieldSetter):
    def _prepare_value(self, value):
        if value is None:
            return None

        if not isinstance(value, list):
            raise TypeError(
                f'{self.name} expected to be list of {self.field_type}, got {value} instead')

        value = [prepare_value(item, self.field_type, self.field_instance, self.name)
                 for item in value]
        return _List(self.field_type, self.field_instance, self.name, value)


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
    subnet = auto()


class JsonNumericFormat(JsonFormat):
    percentage = auto()


class JsonArrayFormat(JsonFormat):
    table = auto()
    calendar = auto()


class Field:
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
        if issubclass(self.type, int):
            return 'integer'
        if issubclass(self.type, float):
            return 'number'
        if issubclass(self.type, str):
            return 'string'
        if issubclass(self.type, dict):
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
        self._set_name(name)

        getter = FieldGetter(self, self._type, name)
        setter = FieldSetter(self, self._type, name)
        field = NamedProperty(name, getter, setter)
        return field


class ListField(Field):
    """ A single field class, holds information regarding python type checking and json-serialization
        for a list-field
    """

    def get_field(self, name: str):
        """ returns a new python property instance with both getter and setter for the current field list that will get
            installed on a SmartJsonClass derived class. """
        self._set_name(name)
        getter = ListGetter(self, self._type, name)
        setter = ListSetter(self, self._type, name)
        field = NamedProperty(name, getter, setter)
        return field
