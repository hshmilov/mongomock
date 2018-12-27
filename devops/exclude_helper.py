import json
from pathlib import Path

EXCLUDE_LIST_KEY = 'exclude-list'
ADD_TO_EXCLUDE_KEY = 'add-to-exclude'
REMOVE_FROM_EXCLUDE_KEY = 'remove-from-exclude'


class ExcludeHelper:
    def __init__(self, filepath):
        self.path = Path(filepath)
        self.exclude_add = []
        self.exclude_remove = []
        if self.path.is_file():
            as_json = self.path.read_text()
            as_dict = json.loads(as_json)
            print(f'{self.path}: config content: {as_dict}')
            exclude = as_dict[EXCLUDE_LIST_KEY]
            self.exclude_add = exclude.get(ADD_TO_EXCLUDE_KEY, [])
            print(f'{self.path} exclude_add {self.exclude_add}')
            self.exclude_remove = exclude.get(REMOVE_FROM_EXCLUDE_KEY, [])
            print(f'{self.path} exclude_remove {self.exclude_remove}')

    def process_exclude(self, inp_list: list):
        as_set = set(inp_list)
        as_set = as_set.union(self.exclude_add)
        as_set.difference_update(self.exclude_remove)

        print(f'{self.path} resulted exclude: {as_set}')
        return list(as_set)
