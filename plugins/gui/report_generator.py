import logging

logger = logging.getLogger(f"axonius.{__name__}")
from datetime import datetime
from math import pi, cos, sin, floor, ceil

from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
from weasyprint.fonts import FontConfiguration
from cairosvg import svg2png

from gui.consts import ChartTypes

GREY_COLOUR = '#DEDEDE'


class ReportGenerator(object):
    def __init__(self, report_data, template_path, output_path='/tmp/', host='localhost'):
        """

        :param report_data:
        :param template_path:
        :param output_path:
        """
        self.report_data = report_data
        self.template_path = template_path
        self.output_path = output_path
        self.host = host
        self.env = Environment(loader=FileSystemLoader('.'))

        self.templates = {
            'report': self._get_template('axonius_report'),
            'section': self._get_template('report_section'),
            'card': self._get_template('report_card'),
            'pie': self._get_template('summary/pie_chart'),
            'pie_slice': self._get_template('summary/pie_slice'),
            'pie_gradient': self._get_template('summary/pie_gradient'),
            'histogram': self._get_template('summary/histogram_chart'),
            'histogram_bar': self._get_template('summary/histogram_bar'),
            'view': self._get_template('view_data/view'),
            'table': self._get_template('view_data/table'),
            'row': self._get_template('view_data/table_row'),
            'head': self._get_template('view_data/table_head'),
            'data': self._get_template('view_data/table_data')
        }

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
        sections = []
        # Add summary section containing dashboard panels, pre- and user-defined
        sections.append(self.templates['section'].render({'title': 'Summary', 'content': self._create_summary()}))

        # Add section for each adapter with results of its queries
        if self.report_data.get('adapter_data'):
            for adapter in self.report_data['adapter_data']:
                sections.append(self.templates['section'].render(
                    {'title': adapter['name'], 'content': self._create_adapter(adapter['queries'], adapter['views'])}))

        # Add section for all saved queries
        if self.report_data.get('views_data'):
            sections.append(self.templates['section'].render(
                {'title': 'Saved Views', 'content': self._create_data_views()}))

        # Join all sections as the content of the report
        html_data = self.templates['report'].render({'date': now.strftime("%d/%m/%Y"), 'content': '\n'.join(sections)})

        timestamp = now.strftime("%d%m%Y-%H%M%S")
        temp_report_filename = f'{self.output_path}axonius-report_{timestamp}.pdf'
        # with open(f'{self.output_path}axonius-report_{timestamp}.html', 'w') as file:
        #     file.write(html_data)
        font_config = FontConfiguration()
        css = CSS(filename=f'{self.template_path}styles/styles.css', font_config=font_config)
        HTML(string=html_data, base_url=self.template_path).write_pdf(
            temp_report_filename, stylesheets=[css], font_config=font_config)
        return temp_report_filename

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
        summary_content = []
        if self.report_data.get('adapter_devices') and self.report_data['adapter_devices'].get('total_gross') \
                and self.report_data['adapter_devices'].get('total_net'):
            # Adding main summary card - the data discovery
            data_discovery_template = self._get_template('summary/data_discovery')
            summary_content.append(self.templates['card'].render({
                'title': 'Data Discovery',
                'class': 'full',
                'content': data_discovery_template.render({
                    'seen_count': self.report_data['adapter_devices']['total_gross'],
                    'unique_count': self.report_data['adapter_devices']['total_net']
                })}))

        if self.report_data.get('covered_devices'):
            # Adding cards with coverage of network roles
            for coverage_data in self.report_data['covered_devices']:
                coverage_pie_filename = f'{self.output_path}{"_".join(coverage_data["title"].split(" "))}.png'
                svg2png(bytestring=self._create_coverage_pie(coverage_data['portion']), write_to=coverage_pie_filename)
                summary_content.append(self.templates['card'].render({
                    'title': f'{coverage_data["title"]} Coverage',
                    'content': f'<img src="{coverage_pie_filename}">'
                }))

        if self.report_data.get('adapter_devices') and self.report_data['adapter_devices'].get('adapter_count'):
            # Adding card with histogram comparing amount of devices from each adapter
            summary_content.append(self.templates['card'].render({
                'title': 'Devices per Adapter',
                'content': self._create_adapter_histogram()
            }))

        if self.report_data.get('custom_charts'):
            for i, custom_chart in enumerate(self.report_data['custom_charts']):
                if not custom_chart.get('type') or not custom_chart.get('data'):
                    continue
                title = custom_chart.get('name', f'Custom Chart {i}')
                if custom_chart['type'] == ChartTypes.compare.name:
                    content = self._create_query_histogram(custom_chart['data'])
                elif custom_chart['type'] == ChartTypes.intersect.name:
                    query_pie_filename = f'{self.output_path}{"_".join(title.split(" "))}.png'
                    svg2png(bytestring=self._create_query_pie(custom_chart['data']), write_to=query_pie_filename)
                    content = f'<img src="{query_pie_filename}">'
                if not content:
                    continue
                summary_content.append(self.templates['card'].render({'title': title, 'content': content}))
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
                'path': slice_def['path'], 'colour': colours[int(floor(portion * 4))],
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

    def _create_adapter_histogram(self):
        """
        Sort the adapters found in the report data by descending size and create a histogram for them

        :param adapter_count:
        :return:
        """
        adapters = self.report_data['adapter_devices']['adapter_count']
        adapters.sort(key=lambda x: x['count'], reverse=True)
        return self._create_histogram(adapters, 6)

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
        max = data[0].get('count', 1)
        for item in data[:limit]:
            if not item.get('name') or not item.get('count'):
                continue
            width = 20 + ((180 * item['count']) / max)
            parameters = {'quantity': item['count'], 'width': width, 'name': item['name']}
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
        total = queries_data[0].get('count', 1)
        portions = []
        for item in queries_data[1:]:
            if item.get('count'):
                portions.append(item['count'] / total)
                queries_data[0]['count'] = queries_data[0]['count'] - item['count']
        portions.insert(0, queries_data[0]['count'] / total)

        colours = [GREY_COLOUR, '#1593C5', 'url(#intersection)', '#15C59E']
        slices = []
        for i, slice_def in enumerate(self._calculate_pie_slices(portions)):
            parameters = {'path': slice_def['path'], 'colour': colours[i]}
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
                results.append(f"<h3>{client_name}</h3>")
                for view_data in views:
                    if not view_data.get('name') or not view_data.get('data'):
                        continue

                    results.append(self._create_data_view(view_data))
        return '\n'.join(results)

    def _create_data_views(self):
        views = []
        for view_data in self.report_data['views_data']:
            if not view_data.get('name') or not view_data.get('data'):
                continue

            views.append(self._create_data_view(view_data))
        return '\n'.join(views)

    def _create_data_view(self, view_data):
        """
        Create tables containing each view's data according to given fields.
        Number of coloumns is limited such that fits in a page.

        :param viewa_data:
        :return:
        """
        current_fields = view_data['fields'][0:6]
        heads = [self.templates['head'].render({'content': list(field.keys())[0]}) for field in current_fields]
        rows = []
        for item in view_data['data']:
            item_values = []
            for field in current_fields:
                value = item[list(field.values())[0]]
                if isinstance(value, list):
                    canonized_value = [str(x) for x in value]
                    value = ','.join(canonized_value)
                item_values.append(self.templates['data'].render({'content': value}))
            rows.append(self.templates['row'].render({'content': '\n'.join(item_values)}))

        fields_len = len(view_data['fields'])
        return self.templates['view'].render({
            'title': view_data['name'], 'cols_total': fields_len, 'cols_current': min(fields_len, 6),
            'view_all': '' if not view_data.get('entity') else
            f' - <a href="https://{self.host}/{view_data["entity"]}?view={view_data["name"]}" class="c-blue">view all</a>',
            'content': self.templates['table'].render({
                'head_content': self.templates['row'].render({'content': '\n'.join(heads)}),
                'body_content': '\n'.join(rows)
            })
        })
