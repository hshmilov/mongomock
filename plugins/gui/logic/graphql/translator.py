"""
{'$and': [{'$or': [{'specific_data.data.hostname': {'$options': 'i',
      '$regex': '33'}},
    {'specific_data.data.name': 'yy'}]},
  {'specific_data.data.name': {'$options': 'i', '$regex': '77$'}}]}

print(translate_aql('(specific_data.data.hostname == regex("66", "i")) or (specific_data.data.hostname == "ttt")'))
print(translate_aql('(specific_data.data.last_seen >= date("NOW - 7d"))'))
print(translate_aql('not (specific_data.data.last_seen >= date("NOW - 30d"))'))
print(translate_aql('(specific_data.data.adapter_properties == "Agent")
or (specific_data.data.adapter_properties == "Manager")'))
print(translate_aql('(specific_data.data.network_interfaces.ips == size(1))'))
print(translate_aql('not (specific_data.data.adapter_properties == "Agent")'))
print(translate_aql(
    '((adapters_data.active_directory_adapter.id == ({"$exists":true,"$ne":""})))
    and (specific_data.data.last_seen >= date("NOW - 30d")) and
    not (specific_data.data.adapter_properties == "Agent")'))
print(Translator(EntityType.Devices).translate('(specific_data.data.adapter_properties == "Vulnerability_Assessment")'))
"""
# pylint: disable=invalid-string-quote, invalid-triple-quote
import typing
import datetime
from cachetools import LFUCache, cached

import axonius.pql as _pql
from axonius.entities import EntityType
from axonius.utils.axonius_query_language import process_filter
from gui.logic.graphql.builder import GqlQuery

AQL_LOGICAL_AND = '$and'
AQL_LOGICAL_OR = '$or'

TERM_CONVERTER = {
    '$and': 'AND',
    '$or': 'OR',
    '$not': 'NOT',
}

# Mapping of all methods based on the operator
VALUE_COMPARISON_METHODS = {
    '$regex': lambda x: {'ilike': f'%{x.lstrip("^").rstrip("$")}%'},
    '$not_regex': lambda x: {'not_ilike': f'%{x.lstrip("^").rstrip("$")}%'},
    '$eq': lambda x: {'eq': x},
    '$neq': lambda x: {'neq': x},
    'exists': lambda x: {'exists': x},
    '$in': lambda x: {'in': x},
    '$not_in': lambda x: {'not_in': x},
    '$lt': lambda x: {'lt': _value_converter(x)},
    '$gt': lambda x: {'gt': _value_converter(x)},
    '$lte': lambda x: {'lte': _value_converter(x)},
    '$gte': lambda x: {'gte': _value_converter(x)},
    '$not': lambda x: _build_value(x, reverse=True),
    '$size': lambda x: {"size": x},
    '$overlap': lambda x: {"overlap": x if isinstance(x, list) else [x]},
    '$no_overlap': lambda x: {"no_overlap": x if isinstance(x, list) else [x]}

}

# When $not is received we swap the operator to it's reversed state
REVERSE_OPERATORS = {
    '$eq': '$neq',
    '$lt': '$gte',
    '$lte': '$gt',
    '$gte': '$lt',
    '$gt': '$lte',
    '$in': '$not_in',
    '$regex': '$not_regex',
    '$overlap': '$no_overlap'
}

# Special key methods, this is done for inner document keys that have been turned to relations
KEY_NAME_METHODS = {
    'adapter_properties': lambda k, v: {'adapter': {"properties": _build_value(v, operator_override="$overlap",
                                                                               reverse=('$not' in v))}},
    'network_interfaces.ips': lambda k, v: {'interfaces': {'ipAddrs': _build_value(v)}}
}


class GqlObject(str):
    pass


class GqlField(str):
    pass


class GqlNotSupported(str):
    """
    GqlNotSupported will skip the field but won't crash the query
    """


BUILDER_CONVERTERS = {
    'adapterDevices': GqlObject('adapterDevices'),
    'adapterUsers': GqlObject('adapterUsers'),
    'adapters': GqlField('adapterNames'),
    'os': GqlObject('os'),
    'network_interfaces': GqlObject('interfaces'),
    # For now until labels are supported for both users and devices
    'labels': GqlNotSupported('tags.name'),
    'tags': GqlObject('tags'),
    'is_admin': GqlField('admin'),
    'is_suspended': GqlField('suspended'),
    'is_local': GqlField('local'),
    'is_delegated_admin': GqlField('delegatedAdmin'),
    'is_mfa_enforced': GqlField('mfaEnforced'),
    'is_mfa_enrolled': GqlField('mfaEnrolled'),
    'is_disabled': GqlField('disabled'),
    'is_locked': GqlField('locked'),
    'ips': GqlField('ipAddrs'),
    'mac': GqlField('macAddr'),
    'image': GqlNotSupported('image'),
}


class Translator:
    def __init__(self, entity_type: EntityType):
        self._entity_type = entity_type
        self._specific_data_converter = 'adapterDevices' if entity_type == EntityType.Devices else 'adapterUsers'
        self._bool_exp_type = 'device' if entity_type == EntityType.Devices else 'user'

    @cached(cache=LFUCache(maxsize=64), key=lambda _, aql: hash(aql))
    def translate(self, aql):
        processed_aql = process_filter(aql, None)
        tokenized_aql = _pql.find(processed_aql)
        return self._translate_aql(tokenized_aql)

    @cached(cache=LFUCache(maxsize=64), key=lambda _, fields_query: hash(fields_query))
    def build_gql(self, fields_query: str):
        fields = fields_query.split(',')
        gql = GqlQuery().query(
            name=self._entity_type.name.lower(),
            input={'where': '$where', 'limit': '$limit', 'offset': '$offset', 'orderBy': '$orderBy'})
        gql = gql.operation('query', name="GQLQuery",
                            input={'$where': f'{self._bool_exp_type}_bool_exp!',
                                   '$limit': 'Int = 20',
                                   '$offset': 'Int = 0',
                                   '$orderBy': f'[{self._bool_exp_type}_order_by!]'}
                            )
        gql.add_fields('adapterCount', 'id', '_compatibilityAPI')
        created_gql = {}
        for field in fields:
            self._parse_field(field, created_gql, gql)
        return gql.generate()

    def _parse_field(self, field: str, created_gql: dict, current: GqlQuery):
        if field.startswith('specific_data.data'):
            field = field.replace('specific_data.data', self._specific_data_converter)

        # split the field
        if "." not in field:
            gql_field = BUILDER_CONVERTERS.get(field, GqlField(field))
            if isinstance(gql_field, GqlObject):
                self._parse_field(gql_field, created_gql, current)
                return
            if isinstance(gql_field, GqlNotSupported):
                return
            current.add_fields(_to_lower_camel_case(gql_field))
            return

        _type, rest = field.split('.', 1)
        gql_field = BUILDER_CONVERTERS.get(_type)
        if not gql_field:
            raise NotImplementedError(f'Unknown {_type}')

        gql = created_gql.get(gql_field)
        if not gql:
            gql = GqlQuery(name=gql_field)
            created_gql[gql_field] = gql
            current.add_fields(gql)
        self._parse_field(rest, created_gql, gql)

    def _translate_aql(self, tokenized_aql):
        gql = {}
        for k, v in tokenized_aql.items():
            if k in [AQL_LOGICAL_AND, AQL_LOGICAL_OR]:
                gql.update(self._translate_logical_aql(k, v))
                continue
            gql.update(self._build_comparison(k, v))
        return gql

    def _translate_logical_aql(self, logical_type: typing.AnyStr, value: typing.List) -> typing.Dict:
        converted_values = []
        for item in value:
            converted_values.append(self._translate_aql(item))
        return {TERM_CONVERTER[logical_type]: converted_values}

    def _build_comparison(self, key, value):
        if key.startswith('specific_data.data'):
            return {
                self._specific_data_converter: self._build_comparison(key.replace('specific_data.data.', ''), value)
            }
        if key.startswith('adapters_data'):
            return self._build_adapter_comparison(key.replace('adapters_data.', ''), value)
        if key.startswith('os'):
            return {self._specific_data_converter: self._build_adapter_comparison(key.replace('os.', ''), value)}

        method = KEY_NAME_METHODS.get(key)
        if method:
            return method(key, value)
        return {TERM_CONVERTER.get(key, _to_lower_camel_case(key)): _build_value(value)}

    def _build_adapter_comparison(self, key, value):
        adapter_type, prop = key.split('.')
        if prop == 'id':
            return {self._specific_data_converter: {'adapterName': {'eq': adapter_type}}}
        return {self._specific_data_converter: {'adapterName': {'eq': adapter_type}, prop: _build_value(value)}}


# ====================================== Private Methods ====================================== #

def _to_lower_camel_case(snake_str):
    if '_' not in snake_str:
        return snake_str
    first, *others = snake_str.split('_')
    return ''.join([first.lower(), *map(str.title, others)])


def _get_op_method(operator, reverse=False):
    if reverse:
        return VALUE_COMPARISON_METHODS.get(REVERSE_OPERATORS.get(operator))
    return VALUE_COMPARISON_METHODS.get(operator)


def _build_value(value, operator_override=None, reverse=False):
    if not isinstance(value, dict) and operator_override is None:
        return {'eq': _value_converter(value)}

    if operator_override:
        method = _get_op_method(operator_override, reverse=reverse)
        return method(value)

    for k in value.keys():
        method = _get_op_method(k, reverse=reverse)
        if not method:
            continue
        return method(value[k])
    raise NotImplementedError(value)


def _value_converter(x):
    if isinstance(x, datetime.datetime):
        return int(x.timestamp() * 1000)
    return x
