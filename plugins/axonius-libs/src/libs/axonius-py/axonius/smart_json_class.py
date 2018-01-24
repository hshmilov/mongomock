from collections import OrderedDict
from enum import Enum

from axonius.fields import Field, ListField


"""
SmartJsonClass is a auto-json-serializable class, that allows finer declaration of possible fields and their types.
When inheriting for SmartJsonClass, use the provided Field & ListField classes to declare new fields.
                                    see fields.py for more information about creating new fields.
When setting a field, please note that a TypeError will be raise if the type is a mismatch.
"""


class SmartJsonClassMetaclass(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return OrderedDict()

    def __new__(cls, name, bases, namespace, **kwargs):
        fields = []
        # Iterate all newly defined attributes, *convert* them to a proper
        # property (getter and setter) by calling Field.get_field(attr_name)
        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Field):
                fields.append(attr_value)
                namespace[attr_name] = attr_value.get_field(attr_name)
        # Iterate other bases (support for Mixins):
        for base in bases[1:]:
            for attr_name, attr_value in base.__dict__.items():
                if isinstance(attr_value, Field):
                    fields.append(attr_value)
                    namespace[attr_name] = attr_value.get_field(attr_name)
        # append a list of the original fields to the class
        base_fields = []
        if bases:
            base_fields = getattr(bases[0], 'fields_info', [])
        assert len(set([field.name for field in fields])) == len(fields), 'Found duplicate fields'
        namespace['fields_info'] = base_fields + fields
        result = type.__new__(cls, name, bases, namespace)
        return result


class SmartJsonClass(metaclass=SmartJsonClassMetaclass):
    fields_info = []  # will hold the list of fields that were defined for this class
    required = []  # should contain a list of required fields, if such a list is needed

    def __init__(self, **kwargs):
        """ Creates a new SmartJsonClass and assigns the kwargs as field-values to this instance. """
        self._dict = {}  # will hold the actual values for this instance
        self._names = set()
        for field_names, value in kwargs.items():
            assert field_names in self.fields_info
            setattr(self, field_names, value)

    def __setattr__(self, name, value):
        """ Disable setting attributes not defined as Fields """
        if not name.startswith('_') and not isinstance(getattr(self.__class__, name, None), property):
            raise AttributeError(f'Unknown attribute \'{name}\' for class {self.__class__.__name__}')
        super().__setattr__(name, value)

    def _extend_names(self, name: str, value):
        """ Extends the target_field_list (or the default field list, as implemented in _define_new_name) to contain any
            new keys that are in value. name should be the full-name of the current value.
            value can be of *any type*, supports iterating inner values of dict, list and SmartJsonClass.
        """
        if isinstance(value, dict):
            for key in value:
                self._extend_names(f'{name}.{key}', value[key])
        elif isinstance(value, list):
            for item in value:
                self._extend_names(name, item)
        elif isinstance(value, SmartJsonClass):
            for attr_name in value._names:
                sub_name = f'{name}.{attr_name}'
                if sub_name not in self._names:
                    self._define_new_name(sub_name)
                    self._names.add(sub_name)
        elif name not in self._names:
            self._define_new_name(name)
            self._names.add(name)

    def _define_new_name(self, name: str):
        """ Defines a new full-field-name """

    def to_dict(self):
        """ returns a serialized dict of this instance, can be passes as a json object """
        new_dict = dict(self._dict)
        for key in new_dict:
            if isinstance(new_dict[key], SmartJsonClass):
                new_dict[key] = new_dict[key].to_dict()
            elif isinstance(new_dict[key], list):
                new_list = []
                for item in new_dict[key]:
                    if isinstance(item, SmartJsonClass):
                        item = item.to_dict()
                    new_list.append(item)
                new_dict[key] = new_list
            elif isinstance(new_dict[key], Enum):
                new_dict[key] = new_dict[key].name
        return new_dict

    @classmethod
    def get_fields_info(cls):
        """ A class method; returns a json-scheme of the current class, containing all fields defined under it. """
        value = {"items": list(cls._get_fields_info()), 'type': 'array'}
        if cls.required:
            value['required'] = cls.required
        return value

    @classmethod
    def _get_fields_info(cls):
        """ helper recursive function for get_fields_info """
        for field in cls.fields_info:
            assert isinstance(field, Field)
            item = {'name': field.name, 'title': field.description}
            if issubclass(field.type, SmartJsonClass):
                field_type = list(field.type._get_fields_info())
                if isinstance(field, ListField):
                    field_type = {'items': field_type, 'type': 'array'}
                item['items'] = field_type
                field_type = 'array'
            else:
                field_type = field.json_name
                if isinstance(field, ListField):
                    item['items'] = {'type': field_type}
                    field_type = 'array'
                if field.format is not None:
                    item['format'] = field.format.name.replace('_', '-')
                if field.min is not None:
                    item['minimum'] = field.min
                if field.max is not None:
                    item['maximum'] = field.max
                if field.pattern is not None:
                    item['pattern'] = field.pattern
                if field.enum is not None:
                    enum_values = field.enum
                    if isinstance(enum_values, type) and issubclass(enum_values, Enum):
                        enum_values = [value.name for value in enum_values]
                    item['enum'] = enum_values
            item['type'] = field_type
            yield item
