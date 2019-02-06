import os

from typing import Generator, Type
from glob import iglob
from importlib import import_module

from mockingbird.commons.adapter_parser import AdapterParser


def get_all_parsers() -> Generator[Type[AdapterParser], None, None]:
    for module_path in iglob(os.path.join(os.path.dirname(__file__), '*.py')):
        module_relative = os.path.basename(module_path)
        if not module_relative.startswith('_'):
            module_name = module_relative[:-3]
            class_name = ''.join([module_name_part.capitalize() for module_name_part in str(module_name).split('_')])
            module = import_module(f'mockingbird.mock_adapters.{module_name}')
            parser = getattr(module, f'{class_name}AdapterParser')
            yield parser
