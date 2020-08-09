# pylint: disable=unnecessary-lambda, too-many-locals, too-many-branches, too-many-statements
import time
import json
from collections import defaultdict
from typing import List, Dict

import click
from bson import ObjectId
from tabulate import tabulate


@click.group(name='dashboards')
@click.pass_context
def ax_dashboards(ctx):
    """exports settings outside Axonius"""
    ctx.ensure_object(dict)
    from testing.services.plugins.gui_service import GuiService

    ctx.obj['gui'] = GuiService()


@ax_dashboards.command(name='show')
@click.pass_context
def ax_dashboards_show(ctx):
    """view dashboards"""
    from axonius.consts.gui_consts import DASHBOARD_SPACES_COLLECTION, DASHBOARD_COLLECTION

    gui = ctx.obj['gui']
    spaces = gui.self_database[DASHBOARD_SPACES_COLLECTION].find({'type': {'$ne': 'personal'}})
    dashboards = defaultdict(list)
    for dashboard in gui.self_database[DASHBOARD_COLLECTION].find({}):
        dashboards[str(dashboard['space'])].append(dashboard)

    table = [(x['name'], x['type'], len(dashboards.get(str(x['_id'])) or [])) for x in spaces]

    click.echo(tabulate(table, headers=['Name', 'Type', 'Charts']))


def get_all_queries_from_chart_recursively(item, keys: List[str]):
    """
    Goes over a chart config and exports everything that exists in the list [keys]
    :return:
    """
    if str(item) in keys:
        yield item
    elif isinstance(item, list):
        for sub_item in item:
            yield from get_all_queries_from_chart_recursively(sub_item, keys)
    elif isinstance(item, dict):
        for sub_item in item.values():
            yield from get_all_queries_from_chart_recursively(sub_item, keys)


def set_all_queries_from_chart_recursively(item, old_to_new_map: Dict[str, str]):
    """
    Goes over a chart config recursively. For every key in old_to_new_map, if it exists as value in the chart config,
    it gets replaced to it's value in old_to_new_map.
    :return:
    """

    if isinstance(item, dict):
        for sub_key, sub_item in item.items():
            item[sub_key] = set_all_queries_from_chart_recursively(sub_item, old_to_new_map)
        return item
    if isinstance(item, list):
        return [set_all_queries_from_chart_recursively(x, old_to_new_map) for x in item]
    if str(item) in old_to_new_map:
        return old_to_new_map[str(item)]

    return item


@ax_dashboards.command(name='export')
@click.option('--spaces', '-s', required=True, multiple=True, help='Space(s) to export')
@click.option('--output', '-o', required=True, help='Output file', type=click.File('wt'))
@click.pass_context
def ax_dashboards_export(ctx, spaces, output):
    """export dashboards"""
    from axonius.consts.gui_consts import DASHBOARD_SPACES_COLLECTION, DASHBOARD_COLLECTION
    from axonius.consts.plugin_consts import DEVICE_VIEWS, USER_VIEWS

    gui = ctx.obj['gui']
    all_spaces = {
        str(x['name']): x for x in gui.self_database[DASHBOARD_SPACES_COLLECTION].find({'type': {'$ne': 'personal'}})
    }

    all_device_queries = {
        str(x['_id']): x for x in gui.self_database[DEVICE_VIEWS].find({})
    }

    all_user_queries = {
        str(x['_id']): x for x in gui.self_database[USER_VIEWS].find({})
    }

    all_keys = list(all_device_queries.keys()) + list(all_user_queries.keys())

    spaces_export = {}
    device_queries_export = {}
    user_queries_export = {}

    error = False
    for space in spaces:
        if space in all_spaces.keys():
            spaces_export[str(all_spaces[space]['_id'])] = {
                'space': all_spaces[space],
                'charts': {}
            }
        else:
            click.secho(f'Error: Space {space!r} does not exist', fg='red')
            error = True

    if error:
        raise click.Abort()

    for chart in gui.self_database[DASHBOARD_COLLECTION].find({}):
        if str(chart['space']) in spaces_export:
            spaces_export[str(chart['space'])]['charts'][str(chart['_id'])] = chart
            # Search for all queries that need to be imported
            for oid in get_all_queries_from_chart_recursively(chart.get('config') or {}, all_keys):
                if str(oid) in all_device_queries and str(oid) not in device_queries_export:
                    device_queries_export[str(oid)] = all_device_queries[str(oid)]
                elif str(oid) in all_user_queries and str(oid) not in user_queries_export:
                    user_queries_export[str(oid)] = all_user_queries[str(oid)]

    output.write(
        json.dumps(
            {
                'spaces': spaces_export,
                DEVICE_VIEWS: device_queries_export,
                USER_VIEWS: user_queries_export
            },
            indent=4,
            default=lambda o: str(o)
        )
    )

    click.echo(f'Successfully exported.')


@ax_dashboards.command(name='import')
@click.option('--input', '-i', 'input_json_file', required=True, help='Input file', type=click.File('rt'))
@click.option('--creator', 'creator', default='admin', help='The username of the creator')
@click.option('--replace', is_flag=True, help='Force replace if space exists.')
@click.pass_context
def ax_dashboards_import(ctx, input_json_file, replace, creator):
    """import dashboards"""
    from axonius.consts.gui_consts import DASHBOARD_SPACES_COLLECTION, DASHBOARD_COLLECTION, USERS_COLLECTION
    from axonius.consts.plugin_consts import DEVICE_VIEWS, USER_VIEWS

    gui = ctx.obj['gui']

    try:
        input_json = json.loads(input_json_file.read())
    except Exception:
        click.secho(f'Error: content of input file is not json!', fg='red')
        raise

    assert 'spaces' in input_json
    assert DEVICE_VIEWS in input_json
    assert USER_VIEWS in input_json

    all_spaces = {
        str(x['name']): x for x in gui.self_database[DASHBOARD_SPACES_COLLECTION].find({'type': {'$ne': 'personal'}})
    }

    creator_id = gui.self_database[USERS_COLLECTION].find_one({'user_name': creator})
    if not creator_id:
        click.secho(f'Error: No such user {creator!r}! please specify a different user.')
        raise click.Abort()
    creator_id = creator_id['_id']

    old_oid_to_new_oid_map = {}

    click.secho(f'Importing queries...', fg='green')
    for view_type in [DEVICE_VIEWS, USER_VIEWS]:
        for entity_query_id, entity_query in input_json[view_type].items():
            if 'name' not in entity_query:
                continue
            current = gui.self_database[view_type].find_one({'name': entity_query['name']})
            if current:
                new_oid = str(current['_id'])
                click.secho(f'Query {entity_query["name"]!r} exists ({new_oid!r}), not importing', fg='yellow')
            else:
                entity_query['user_id'] = creator_id
                entity_query['updated_by'] = creator_id
                entity_query['_id'] = ObjectId(entity_query['_id'])
                new_oid = str(gui.self_database[view_type].insert_one(entity_query).inserted_id)
                click.secho(f'Query {entity_query["name"]!r}: imported as {new_oid!r}', fg='green')

            old_oid_to_new_oid_map[str(entity_query_id)] = new_oid

    for dashboard in input_json['spaces'].values():
        space_name = dashboard['space']['name']
        if space_name in all_spaces.keys():
            if replace:
                click.echo(f'Space {space_name!r} exists, going to replace it.')
            else:
                dashboard['space']['name'] += f'-imported-{int(time.time())}'
                dashboard['space']['type'] = 'custom'
                orig_space_name = space_name
                space_name = dashboard['space']['name']
                click.secho(f'Space {orig_space_name!r} exists, importing as {space_name}', fg='yellow')

    for dashboard in input_json['spaces'].values():
        space_name = dashboard['space']['name']
        charts_order = dashboard['space'].get('panels_order')
        dashboard_charts = dashboard['charts']
        assert isinstance(dashboard_charts, dict), 'Expecting charts to be a dictionary'

        if not charts_order:
            charts = dashboard_charts.values()
        else:
            charts = []
            for chart_id in charts_order:
                chart = dashboard_charts.get(chart_id)
                if chart:
                    charts.append(chart)

        old_space = gui.self_database[DASHBOARD_SPACES_COLLECTION].find_one_and_delete({'name': space_name})
        if old_space:
            click.secho(f'Deleting current space {space_name!r}...', fg='yellow')
            gui.self_database[DASHBOARD_COLLECTION].delete_many({'space': old_space['_id']})

        space_to_insert = dashboard['space']
        space_to_insert.pop('_id', None)
        space_to_insert.pop('panels_order', None)

        new_space_id = gui.self_database[DASHBOARD_SPACES_COLLECTION].insert_one(space_to_insert).inserted_id

        panels_order = []
        for chart_to_insert in charts:
            chart_to_insert.pop('_id')
            chart_to_insert['space'] = new_space_id
            chart_to_insert['user_id'] = creator_id

            chart_to_insert = set_all_queries_from_chart_recursively(chart_to_insert, old_oid_to_new_oid_map)

            chart_id = str(gui.self_database[DASHBOARD_COLLECTION].insert_one(chart_to_insert).inserted_id)
            panels_order.append(chart_id)
            click.secho(f'Inserted chart {chart_to_insert["name"]!r} with id {chart_id!r}', fg='green')

        gui.self_database[DASHBOARD_SPACES_COLLECTION].update_one(
            {'_id': new_space_id},
            {'$set': {'panels_order': panels_order}}
        )

        click.secho(f'Inserted space {space_name!r} with id {new_space_id}', fg='green')
