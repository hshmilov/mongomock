from axonius.consts.gui_consts import ChartViews
from cairosvg import svg2png
from weasyprint.fonts import FontConfiguration
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
import uuid
from math import pi, cos, sin, floor
from datetime import datetime
import logging

from axonius.entities import EntityType
from axonius.logging.metric_helper import log_metric
from axonius.plugin_base import PluginBase
from axonius.utils import gui_helpers
from axonius.utils.axonius_query_language import parse_filter
from gui.gui_logic import filter_utils
from gui.gui_logic.adapter_data import adapter_data

logger = logging.getLogger(f'axonius.{__name__}')


GREY_COLOUR = '#DEDEDE'


class ReportGenerator(object):
    def __init__(self, report, dashboard, adapters, default_sort, template_path, output_path='/tmp/', host='localhost'):
        """

        :param report:
        :param template_path:
        :param output_path:
        """
        self.report = report
        self.dashboard = dashboard
        self.adapters = adapters
        self.default_sort = default_sort
        self.report_data = self.get_report_data(self.report)
        self.template_path = template_path
        self.output_path = output_path
        self.host = host
        self.env = Environment(loader=FileSystemLoader('.'))

        self.templates = {
            'report': self._get_template('axonius_report'),
            'section': self._get_template('report_section'),
            'card': self._get_template('report_card'),
            'discovery': self._get_template('summary/data_discovery'),
            'pie': self._get_template('summary/pie_chart'),
            'pie_slice': self._get_template('summary/pie_slice'),
            'pie_gradient': self._get_template('summary/pie_gradient'),
            'histogram': self._get_template('summary/histogram_chart'),
            'histogram_bar': self._get_template('summary/histogram_bar'),
            'summary': self._get_template('summary/summary'),
            'view': self._get_template('view_data/view'),
            'table': self._get_template('view_data/table'),
            'row': self._get_template('view_data/table_row'),
            'head': self._get_template('view_data/table_head'),
            'data': self._get_template('view_data/table_data')
        }

    def get_report_data(self, report):
        """
        Generates the report data from the report.
        :return: the generated report data.
        """
        saved_views = report['views'] if report else None
        include_dashboard = report['include_dashboard'] if report.get('include_dashboard') else False
        include_all_saved_views = report['include_all_saved_views'] if report.get('include_all_saved_views') else False
        include_saved_views = report['include_saved_views'] if report.get('include_saved_views') else False
        report_data = {
            'include_dashboard': include_dashboard,
            'adapter_devices': adapter_data.call_uncached(EntityType.Devices) if include_dashboard else None,
            'adapter_users': adapter_data.call_uncached(EntityType.Users) if include_dashboard else None,
            'custom_charts': list(self.dashboard) if include_dashboard else None,
            'views_data':
                self._get_saved_views_data(include_all_saved_views, saved_views) if include_saved_views else None
        }
        if not include_saved_views:
            log_metric(logger, 'query.report', None)
        if report.get('adapters'):
            report_data['adapter_data'] = self.adapters
        return report_data

    def generate_report_pdf(self):
        """
        Build HTML file representing a report that consists of:
        1. Summary - all Dashboard cards (except lifecycle)
        2. Section per adapter - containing predefined saved queries, with the amount of results for their execution.
        3. Saved Views - a snippet of the entity table's first page, for each saved view (of both entities)
        A pdf file is generated on the basis of the created html and a matching stylesheet.

        :return: The name of the generated pdf file
        """
        now = datetime.now()
        timestamp = now.strftime('%d%m%Y-%H%M%S')
        temp_report_filename = f'{self.output_path}axonius-report_{timestamp}.pdf'
        logger.info(f'Report Generator: PDF generated and saved to ${temp_report_filename}')
        return self.render_html(now).write_pdf(temp_report_filename)

    def render_html(self, current_time):
        sections = []

        if self.report_data.get('include_dashboard'):
            # Add summary section containing dashboard panels, pre- and user-defined
            sections.append(self.templates['section'].render({'title': 'Summary', 'content': self._create_summary()}))

        # Add section for each adapter with results of its queries
        adapter_data = self.report_data.get('adapter_data')
        if adapter_data:
            for adapter in adapter_data:
                sections.append(self.templates['section'].render(
                    {'title': adapter['name'], 'content': self._create_adapter(adapter['queries'], adapter['views'])}))
                logger.info(f'Report Generator, Adapter Section: Added {adapter["name"]} section')

        # Add section for saved views
        if self.report_data.get('views_data'):
            sections.append(self.templates['section'].render(
                {'title': 'Saved Queries', 'content': self._create_data_views()}))
            logger.info(f'Report Generator, Views Section: Added views data section')

        # Join all sections as the content of the report
        html_data = self.templates['report'].render(
            {'date': current_time.strftime('%d/%m/%Y'), 'content': '\n'.join(sections)})
        timestamp = current_time.strftime('%d%m%Y-%H%M%S')
        temp_html_filename = f'{self.output_path}axonius-report_{timestamp}.html'
        with open(temp_html_filename, 'wb') as file:
            file.write(bytes(html_data.encode('utf-8')))
            logger.info(f'Report Generator: HTML created and saved to ${temp_html_filename}')
        font_config = FontConfiguration()
        css = CSS(filename=f'{self.template_path}styles/styles.css', font_config=font_config)

        return HTML(string=html_data, base_url=self.template_path).render(stylesheets=[css], font_config=font_config)

    def _get_template(self, template_name):
        """
        Get the template with requested name, expected to be found in self.template_path and have the extension 'html'
        :param template_name: Name of template file
        :return: The template object
        """
        return self.env.get_template(f'{self.template_path}{template_name}.html')

    def _create_summary(self):
        """
        Create HTML part for each of the dashboard predefined charts as well as those defined by user.

        :return:
        """
        logger.info('Report Generator, Summary Section: Begin')
        summary_content = []
        if self.report_data.get('adapter_devices') and self.report_data['adapter_devices'].get('counters'):
            # Adding card with histogram comparing amount of devices from each adapter
            summary_content.append(self.templates['card'].render({
                'title': 'Device Discovery',
                'content': self._create_adapter_discovery(self.report_data['adapter_devices'], 'devices')
            }))
            logger.info('Report Generator, Summary Section: Added Adapter Devices Discovery Panel')
            if self.report_data.get('adapter_users') and self.report_data['adapter_users'].get('counters'):
                # Adding card with histogram comparing amount of devices from each adapter
                summary_content.append(self.templates['card'].render({
                    'title': 'User Discovery',
                    'content': self._create_adapter_discovery(self.report_data['adapter_users'], 'users')
                }))
                logger.info('Report Generator, Summary Section: Added Adapter Users Discovery Panel')
        if self.report_data.get('covered_devices'):
            # Adding cards with coverage of network roles
            for coverage_data in self.report_data['covered_devices']:
                coverage_pie_filename = f'{self.output_path}{uuid.uuid4().hex}.png'
                svg2png(bytestring=self._create_coverage_pie(coverage_data['portion']), write_to=coverage_pie_filename)
                summary_content.append(self.templates['card'].render({
                    'title': f'{coverage_data["title"]} Coverage',
                    'content': f'<img src="{coverage_pie_filename}">'
                }))
            logger.info(
                f'Report Generator, Summary Section: Added {len(self.report_data["covered_devices"])} Coverage Panels')

        if self.report_data.get('custom_charts'):
            charts_added = 0
            for i, custom_chart in enumerate(self.report_data['custom_charts']):
                title = custom_chart.get('name', f'Custom Chart {i}')
                try:
                    chart_data = custom_chart.get('data')
                    chart_value = None
                    if chart_data and chart_data[0] and not type(chart_data[0]) == list and chart_data[0].get('value'):
                        chart_value = chart_data[0]['value']
                    if not custom_chart.get('metric') or not chart_data \
                            or (custom_chart.get('hide_empty') and chart_data and chart_value in [0, 1]):
                        continue
                    content = None
                    if custom_chart['view'] == ChartViews.histogram.name:
                        content = self._create_query_histogram(custom_chart['data'])
                    elif custom_chart['view'] == ChartViews.pie.name:
                        query_pie_filename = f'{self.output_path}{uuid.uuid4().hex}.png'
                        byte_string = self._create_query_pie(custom_chart['data'])
                        if byte_string == '':
                            continue
                        svg2png(bytestring=byte_string, write_to=query_pie_filename)
                        content = f'<img src="{query_pie_filename}">'
                    elif custom_chart['view'] == ChartViews.summary.name:
                        content = self._create_summary_chart(custom_chart['data'])
                    if not content:
                        continue
                    charts_added += 1
                    summary_content.append(self.templates['card'].render({'title': title, 'content': content}))
                except Exception:
                    logger.exception(f'Problem adding pie chart to reports with title: {title}')
            logger.info(f'Report Generator, Summary Section: Added {charts_added} Custom Panels')
        return '\n'.join(summary_content)

    def _create_coverage_pie(self, portion):
        """
        Create a slice for the given portion, filled with a colour representing the quarter it is in
        and with the percentage as a text to present..
        Then, create a second slice with the remainder of the portion, coloured grey.

        :param portion:
        :return:
        """
        colours = ['#D0011B', '#F6A623', '#4796E4', '#0FBC18']
        slice_defs = self._calculate_pie_slices([1 - portion, portion])
        slices = [self.templates['pie_slice'].render({'path': slice_defs[0]['path'], 'colour': GREY_COLOUR})]
        if portion:
            slice_def = slice_defs[1]
            slices.append(self.templates['pie_slice'].render({
                'path': slice_def['path'], 'colour': colours[int(floor(portion * 3.9))],
                'text': f'{round(portion * 100)}%' if portion else '',
                'x': slice_def['text_x'], 'y': slice_def['text_y']
            }))

        return self.templates['pie'].render({'content': '\n'.join(slices)})

    def _calculate_pie_slices(self, portions):
        """
        Calculate each slice's path, which starts at previous slice's position, arches to the point calculated
        by adding current portion and ends in the center of the circle.

        :param portions:
        :return:
        """
        slices = []
        cumulative_portion = 0
        for portion in portions:
            (start_x, start_y) = self._calculate_coordinates(cumulative_portion)
            cumulative_portion += portion / 2
            (middle_x, middle_y) = self._calculate_coordinates(cumulative_portion)
            cumulative_portion += portion / 2
            (end_x, end_y) = self._calculate_coordinates(cumulative_portion)
            slices.append({
                'path': f'M {start_x} {start_y} A 1 1 0 {1 if portion > .5 else 0} 1 {end_x} {end_y} L 0 0',
                'text_x': middle_x * 0.7, 'text_y': middle_y * (0.8 if middle_y > 0 else 0.5)
            })
        return slices

    def _calculate_coordinates(self, portion):
        """
        :param portion: Wanted percentage for the slice
        :return: (x, y) for the point on the circle that represents given portion
        """
        return (cos(2 * pi * portion), sin(2 * pi * portion))

    def _create_adapter_discovery(self, discovery_data, entity_name):
        """
        Sort the adapters found in the report data by descending size and create a histogram for them

        :param adapter_count:
        :return:
        """
        adapters = discovery_data['counters']
        adapters.sort(key=lambda x: x['value'], reverse=True)
        return self.templates['discovery'].render({
            'entities': entity_name, 'entity': entity_name[:-1],
            'histogram': self._create_histogram(adapters, 6),
            'seen': discovery_data['seen'], 'unique': discovery_data['unique']
        })

    def _create_query_histogram(self, queries_data):
        return self._create_histogram(queries_data, 4, True)

    def _create_histogram(self, data, limit, textual=False):
        """
        Create a bar for each item of given data, with width according to its count and relative to the largest data.
        Combine create bars to a histogram, with remainder indicating amount of bars not shown due to limit.

        :param data:
        :param limit: How many bars to show - textual takes up double row per bar
        :param textual:
        :return:
        """
        bars = []
        max = data[0].get('value', 1)
        for item in data[1:]:
            if item.get('value', 1) > max:
                max = item['value']
        for item in data[:limit]:
            if not item.get('name'):
                continue
            count = item.get('value', 0)
            width = ((180 * count) / max)
            if item.get('meta'):
                count = f'{count} ({item["meta"]})'
            parameters = {'quantity': count, 'width': width, 'name': item['name']}
            if textual:
                parameters['title'] = item['name']
                parameters['class'] = 'd-none'
            bars.append(self.templates['histogram_bar'].render(parameters))
        if not bars:
            return ''
        return self.templates['histogram'].render({'content': '\n'.join(bars),
                                                   'remainder': f'+{len(data) - limit}' if len(data) > limit else ''})

    def _create_query_pie(self, queries_data):
        """
        Create slice for each data returned for the query, after converting each absolute count to be proportional to
        the main query's count

        :param queries_data:
        :return:
        """
        queries = [item for item in queries_data[1:] if item.get('value')]
        queries.insert(0, queries_data[0])
        portions = [item['value'] for item in queries]

        colours = [GREY_COLOUR, '#15C59E', '#15ACB2', '#1593C5', '#B932BB', '#8A32BB', '#5A32BB']
        slices = []
        for i, slice_def in enumerate(self._calculate_pie_slices(portions)):
            parameters = {'path': slice_def['path'],
                          'colour': 'url(#intersection)' if queries[i].get('intersection') else colours[
                              i % len(colours)]}
            if i:
                parameters['text'] = f'{round(portions[i] * 100)}%' if i else ''
                parameters['x'] = slice_def['text_x']
                parameters['y'] = slice_def['text_y']
            slices.append(self.templates['pie_slice'].render(parameters))

        if not slices:
            return ''
        return self.templates['pie'].render({
            'defs': self.templates['pie_gradient'].render({'colour1': colours[1], 'colour2': colours[3]}),
            'content': '\n'.join(slices)
        })

    def _create_summary_chart(self, data):
        """
        Create a bar for each item of given data, with width according to its count and relative to the largest data.
        Combine create bars to a histogram, with remainder indicating amount of bars not shown due to limit.

        :param data:
        :param limit: How many bars to show - textual takes up double row per bar
        :param textual:
        :return:
        """
        value = data[0].get('value', 0)
        title = data[0].get('name', 0)

        return self.templates['summary'].render({'value': value,
                                                 'title': title})

    def _create_adapter(self, queries, views):
        """
        Add a box for each query result count and name, with the appropriate colour if it's negative.

        :param queries:
        :return:
        """
        query_template = self._get_template('adapter/query_result')
        results = []
        for query in queries:
            results.append(query_template.render({
                'host': self.host, 'entity': query['entity'],
                'name': query['name'], 'count': query['count'],
                'colour': 'red' if query.get('negative', False) else 'orange'
            }))
        if views is not None:
            for client_name, views in views.items():
                results.append(f'<h3>{client_name}</h3>')
                for view_data in views:
                    if not view_data.get('name') or not view_data.get('data'):
                        continue

                    results.append(self._create_data_view(view_data))
        return '\n'.join(results)

    def _create_data_views(self):
        views = []
        added_views = 0
        for view_data in self.report_data['views_data']:
            views.append(self._create_data_view(view_data))
            added_views += 1

        logger.info(f'Report Generator, Saved Views: Added {added_views}')
        return '\n'.join(views)

    def _create_data_view(self, view_data):
        """
        Create tables containing each view's data according to given fields.
        Number of coloumns is limited such that fits in a page.

        :param viewa_data:
        :return:
        """
        good_fields = [field for field in view_data['fields'] if list(field.values())[0] != 'specific_data.data.image']
        current_fields = good_fields[0:6]
        heads = [self.templates['head'].render({'content': list(field.keys())[0]}) for field in current_fields]
        rows = []
        for item in view_data['data']:
            item_values = []
            for field in current_fields:
                value = item.get(list(field.values())[0], '')
                if isinstance(value, list):
                    canonized_value = [str(x) for x in value]
                    value = ','.join(canonized_value)
                item_values.append(self.templates['data'].render({'content': value}))
            rows.append(self.templates['row'].render({'content': '\n'.join(item_values)}))

        render_params = {
            'title': view_data['name'],
            'cols_total': len(view_data['fields']), 'cols_current': min(len(good_fields), 6),
            'content': self.templates['table'].render({
                'head_content': self.templates['row'].render({'content': '\n'.join(heads)}),
                'body_content': '\n'.join(rows)
            })
        }
        if view_data.get('entity'):
            render_params['link_start'] = f'<a href="https://{self.host}/{view_data["entity"]}' \
                                          f'?view={view_data["name"]}" class="c-blue">'
            render_params['link_end'] = '</a>'
            render_params['view_all'] = f' - {render_params["link_start"]}view all{render_params["link_end"]}'
        return self.templates['view'].render(render_params)

    def _get_saved_views_data(self, include_all_saved_views=True, saved_queries=None):
        """
        For each entity in system, fetch all saved views.
        For each view, fetch first page of entities - filtered, projected, sorted_endpoint according to it's definition.

        :return: Lists of the view names along with the list of results and list of field headers, with pretty names.
        """
        logger.info('Getting views data')
        views_data = []
        query_per_entity = {}
        for saved_query in saved_queries:
            entity = saved_query['entity']
            name = saved_query['name']
            if entity not in query_per_entity:
                query_per_entity[entity] = []
            query_per_entity[entity].append(name)
        saved_views_filter = None
        if include_all_saved_views:
            saved_views_filter = gui_helpers.filter_archived({
                'query_type': 'saved',
                '$or': [
                    {
                        'predefined': False
                    },
                    {
                        'predefined': {
                            '$exists': False
                        }
                    }
                ]
            })
        for entity in EntityType:
            field_to_title = self._get_field_titles(entity)
            # Fetch only saved views that were added by user, excluding out-of-the-box queries
            if query_per_entity.get(entity.name.lower()) and not include_all_saved_views:
                saved_views_filter = filter_utils.filter_by_name(query_per_entity[entity.name.lower()])

            if not saved_views_filter:
                continue

            saved_views = PluginBase.Instance.gui_dbs.entity_query_views_db_map[entity].find(saved_views_filter)
            for view_doc in saved_views:
                try:
                    view = view_doc.get('view')
                    if view:
                        filter_query = view.get('query', {}).get('filter', '')
                        log_metric(logger, 'query.report', filter_query)
                        field_list = view.get('fields', [])
                        views_data.append({
                            'name': view_doc.get('name'), 'entity': entity.value,
                            'fields': [{field_to_title.get(field, field): field} for field in field_list],
                            'data': list(gui_helpers.get_entities(limit=view.get('pageSize', 20),
                                                                  skip=0,
                                                                  view_filter=parse_filter(filter_query),
                                                                  sort=gui_helpers.get_sort(view),
                                                                  projection={field: 1 for field in field_list},
                                                                  entity_type=entity,
                                                                  default_sort=self.default_sort))
                        })
                except Exception:
                    logger.exception('Problem with View {} ViewDoc {}'.format(view_doc.get('name'), str(view_doc)))
        logger.info('query.saved_views {}'.format(views_data))
        return views_data

    def _get_field_titles(self, entity):
        current_entity_fields = gui_helpers.entity_fields(entity)
        name_to_title = {}
        for field in current_entity_fields['generic']:
            name_to_title[field['name']] = field['title']
        for type in current_entity_fields['specific']:
            for field in current_entity_fields['specific'][type]:
                name_to_title[field['name']] = field['title']
        return name_to_title
