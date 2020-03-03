GENERIC_ADAPTER = 'Aggregated'
# String to use in headers for generic fields

PROCESS_TOO_COMPLEX = 'too_complex'
# processor to use for a complex field under a complex fields

PROCESS_COMPLEX = 'complex'
# processor to use for a complex field at the root

PROCESS_SIMPLE = 'simple'
# processor to use for simple field of (str,int,bool,float)

PROCESS_SIMPLE_ARRAY = 'simple_array'
# processor to use for simple field of list of (str,int,bool,float)

PROCESS_UNKNOWN = 'unknown'
# processor to use when we run out of smart ideas

PROCESS_SIMPLES = [PROCESS_SIMPLE, PROCESS_SIMPLE_ARRAY, PROCESS_UNKNOWN]
# right now, we process all of as simples

TOO_COMPLEX_STR = 'Complex fields with complex sub fields are too complex for CSV'
# value to populate cell with when field is too complex

SIMPLE_TYPES = ['string', 'integer', 'number', 'bool']
# field['type'] values that should be considered simple

CELL_JOIN_DEFAULT = '\n'
# cell joiner to use as default

CELL_MAX_LEN = 30000
# max cell character length in excel, cells longer this will be trimmed to this

CELL_MAX_STR = f'MAX CELL LENGTH OF {CELL_MAX_LEN} EXCEEDED'
# msg to add to cell when trimmed by CELL_MAX_LEN

DTFMT = '%Y-%m-%d %H:%M:%S'
# format to use when serializing fields with datatime values

MAX_ROWS_LEN = 1048500
# max row count in excel, entities more than this will be trimmed to this

MAX_ROWS_STR = f'MAX ROW LIMIT OF {MAX_ROWS_LEN} EXCEEDED'
# a fake entry with this as the first columns value will be added to top of CSV if MAX_ROWS_LEN is hit
