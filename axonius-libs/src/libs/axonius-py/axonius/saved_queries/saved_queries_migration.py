from typing import Dict, List, Tuple
from pymongo import UpdateOne
from pymongo.collection import Collection


def handle_existing_saved_queries(collection: Collection):
    """
    Iterate over all saved queries, updating the relevant queries with the new value (id of a
    referenced query) and updating the filter.
    :param collection
    :return: List of tuples, of query and it's direct references.
    """
    try:
        total_of_queries, queries_references = _get_saved_queries_info_for_entity(collection)

        references = []
        for query_id, query_references in queries_references.items():
            references.append((query_id, [referenced for referenced in query_references[0]]))
        return references

    except Exception as e:
        print(f'Error while getting saved queries info {str(e)}')
        raise


def _get_saved_queries_info_for_entity(entity_views_collection: Collection) -> Tuple[int, List[str],
                                                                                     List[str], List[str]]:
    """
    For each entity type (devices, users) return the saved queries relevant info.
    :param entity_views_collection
    :return: Tuple of - (number of saved queries referencing another saved query, list of private saved queries that
    reference another saved query, list of saved queries referencing a removed query and a list of queries that
    referencing another query and being referenced as well).
    """
    queries_references = {}  # A: ( [reference_to], [referenced_by] )

    # all queries referencing a saved query.
    query = {
        'query_type': 'saved',
        'view.query.expressions.field': 'saved_query',
        '$or': [
            {
                'predefined': {
                    '$exists': False
                }
            },
            {
                'predefined': False
            },
        ]
    }

    num_of_matching_queries = entity_views_collection.count_documents(query)
    print(f'num_of_matching_queries: {num_of_matching_queries}')
    if num_of_matching_queries > 0:
        aql_to_query_name_mapping = _get_aql_to_queries_mapping(entity_views_collection)
        _iterate_entity_views(aql_to_query_name_mapping, queries_references, entity_views_collection, query)
    num_of_queries = num_of_matching_queries

    return num_of_queries, queries_references


def _iterate_entity_views(aql_to_query_name_mapping: Dict[str, List[str]],
                          queries_references: Dict[str, Tuple[set, set]],
                          entity_views_collection: Collection,
                          query: Dict):
    """
    This method iterates devices_views/users_views saved queries and appends the data to the
    relevant set.
    :param entity
    :param entity_views_queries list of saved queries from mongo
    :param aql_to_query_name_mapping mapping between AQL expression to it's corresponding query names (as one AQL
    could exists in multiple queries).
    :param queries_references mapping between query name to a tuple of two sets, one includes the queries names
    that the query reference to, and the other is a set of queries referencing to this query.
    """
    updates = []
    for saved_query in entity_views_collection.find(
            query,
            projection={'name': True, 'view': True, 'private': True, 'archived': True}):
        query_id = str(saved_query.get('_id'))
        query_name = saved_query.get('name')

        expressions = saved_query.get('view', {}).get('query', {}).get('expressions', [])
        query_filter = saved_query.get('view', {}).get('query', {}).get('filter', '')
        query_only_expressions_filter = saved_query.get('view', {}).get('query', {}).get('onlyExpressionsFilter', '')
        if not expressions:
            print(f'No expressions found for: {query_name}')
            continue

        updated_expressions = []
        for expression in expressions:
            if expression.get('field') == 'saved_query':
                updated_expression, query_filter, query_only_expressions_filter = _handle_expression_query(
                    expression, query_filter, query_only_expressions_filter, query_name,
                    query_id, aql_to_query_name_mapping,
                    queries_references)
                updated_expressions.append(updated_expression)
            else:
                updated_expressions.append(expression)

        updates.append(UpdateOne(
            {
                '_id': saved_query.get('_id')
            },
            {
                '$set': {
                    'view.query.expressions': updated_expressions,
                    'view.query.filter': query_filter,
                    'view.query.onlyExpressionsFilter': query_only_expressions_filter
                }
            }))

        # Update base rules.
    if len(updates) > 1000:
        _write_bulk_in_chunks(entity_views_collection, updates)
    entity_views_collection.bulk_write(updates)


def _write_bulk_in_chunks(collection: Collection, updates: List[Dict]):
    total_updates = 0
    while total_updates < len(updates):
        next_chunk = updates[:1000]
        del updates[:1000]
        total_updates += len(next_chunk)
        collection.bulk_write(next_chunk)


def _handle_expression_query(expression: Dict, query_filter: str, query_only_expressions_filter: str, query_name: str,
                             query_id: str, aql_to_query_name_mapping: Dict[str, List[str]],
                             queries_references: Dict[str, Tuple[set, set]]):
    """
    This method receive a single expression from expressions array inside a saved query, and adds the query
    to the relevant object.

    :param expression a single expression that belongs to a saved query.
    :param query_filter the full filter of an existing query.
    :param query_only_expressions_filter
    :param query_name the query that this expression belongs to.
    :param query_id
    :param aql_to_query_name_mapping mapping between AQL expression to it's corresponding query names (as one AQL
    could exists in multiple queries).
    :param queries_references mapping between query name to a tuple of two lists, one includes the queries names
    that the query reference to, and the other is a list of queries referencing to this query.
    :param removed_queries_references a list of tuples where the first element is the query name which reference
    to a removed query and the second element is the referenced AQL (removed query).
    """
    expression_aql = expression.get('value')
    if expression_aql:
        matching_queries = _find_aql_matching_query_name(expression_aql, aql_to_query_name_mapping)
        if matching_queries:
            if not queries_references.get(query_id):
                queries_references[query_id] = (set(), query_name)

            if len(matching_queries) > 1:
                print(f'[MULTIPLE_MATCH - multiple match found for {query_name}'
                      f' and AQL of {expression_aql} - {matching_queries}')
                # When multiple matching detected, the reference is not valid.
                expression['value'] = ''
            else:
                matching_query = matching_queries[0]
                referenced_query_id = str(matching_query.get('_id'))

                # Adding reference query_id -> referenced_query_id
                queries_references[query_id][0].add(referenced_query_id)

                # updating the existing expression
                expression['value'] = referenced_query_id
                logic_op = expression.get('logicOp')
                expression['filter'] = f'{logic_op} ({{{{QueryID={referenced_query_id}}}}})'\
                    if logic_op \
                    else f'({{{{QueryID={referenced_query_id}}}}})'
                query_filter = _replace_filter_with_query_id_placeholder(query_filter, referenced_query_id,
                                                                         expression_aql)
                query_only_expressions_filter = _replace_filter_with_query_id_placeholder(query_only_expressions_filter,
                                                                                          referenced_query_id,
                                                                                          expression_aql)
        else:
            print(f'Unable to find AQL match for query: {query_id} with aql: {expression_aql}')
            expression['value'] = ''

    return expression, query_filter, query_only_expressions_filter


def _replace_filter_with_query_id_placeholder(query_filter, query_id, query_aql):
    str_to_replace = f'(({query_aql}))'
    return query_filter.replace(str_to_replace, f'({{{{QueryID={query_id}}}}})')


def _find_aql_matching_query_name(aql: str, aql_mapping) -> List[str]:
    queries = aql_mapping.get(aql)
    if queries:
        return queries
    return None


def _get_aql_to_queries_mapping(collection) -> Dict[str, List[str]]:
    """
    Function that returns a mapping between an AQL to it's corresponding query name(s), because
    a single aql could match multiple queries.
    :return: Dict
    """
    mapping = {}
    query = {
        'query_type': 'saved',
        '$or': [
            {
                'predefined': {
                    '$exists': False
                }
            },
            {
                'predefined': False
            },
        ]
    }

    for query in collection.find(query, projection={'name': True, 'view': True, 'private': True, 'archived': True}):
        query_aql = query.get('view', {}).get('query', {}).get('filter')
        if query_aql:
            if not mapping.get(query_aql):
                mapping[query_aql] = []

            query_name = query.get('name')
            query_id = query.get('_id')

            mapping[query_aql].append({
                'name': query_name,
                '_id': query_id
            })

    return mapping
