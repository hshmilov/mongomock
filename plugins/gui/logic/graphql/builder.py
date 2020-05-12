"""
Builder taken from https://github.com/youyo/gql-query-builder/tree/master/gql_query_builder
converted to support term changing (field name changing etc')
"""
# pylint: disable=line-too-long, invalid-string-quote, no-self-use, redefined-builtin, dangerous-default-value, bad-option-value
# coding: utf-8
from typing import Dict, List, Union


class GqlQuery:
    def __init__(self, name=None, condition_expression=None) -> None:
        self.object: str = ''
        self.query_field: str = ''
        self.operation_field: str = ''
        self.fragment_field: str = ''
        self.fields: List = []
        self.name = name if name else ''
        self.condition_expression = condition_expression if condition_expression else ''

    def remove_duplicate_spaces(self, query: str) -> str:
        return " ".join(query.split())

    def __str__(self):
        return self.generate()

    @property
    def return_field(self):
        query = '{ ' + " ".join([str(f) for f in self.fields]) + ' }'
        if self.name != '':
            if self.condition_expression != '':
                query = f'{self.name} {self.condition_expression} {query}'
            else:
                query = f'{self.name} {query}'
        return query

    def add_fields(self, *fields):
        self.fields.extend(fields)
        return self

    def query(self, name: str, alias: str = '', input: Dict[str, Union[str, int]] = {}):
        self.query_field = name
        inputs: List[str] = []
        if input != {}:
            for key, value in input.items():
                inputs.append(f'{key}: {value}')
            self.query_field = self.query_field + '(' + ", ".join(inputs) + ')'
        if alias != '':
            self.query_field = f'{alias}: {self.query_field}'

        return self

    def operation(self, query_type: str = 'query', name: str = '', input: Dict[str, Union[str, int]] = {}, queries: List[str] = []):
        self.operation_field = query_type
        inputs: List[str] = []
        if name != '':
            self.operation_field = f'{self.operation_field} {name}'
            if input != {}:
                for key, value in input.items():
                    inputs.append(f'{key}: {value}')
                self.operation_field = self.operation_field + '(' + ", ".join(inputs) + ')'

        if queries != []:
            self.object = self.operation_field + ' { ' + " ".join(queries) + ' }'

        return self

    def fragment(self, name: str, interface: str):
        self.fragment_field = f'fragment {name} on {interface}'
        return self

    def generate(self) -> str:
        if self.fragment_field != '':
            self.object = f'{self.fragment_field} {self.return_field}'
        else:
            if self.object == '' and self.operation_field == '' and self.query_field == '':
                self.object = self.return_field
            elif self.object == '' and self.operation_field == '':
                self.object = self.query_field + ' ' + self.return_field
            elif self.object == '':
                self.object = self.operation_field + ' { ' + self.query_field + ' ' + self.return_field + ' }'

        return self.remove_duplicate_spaces(self.object)
