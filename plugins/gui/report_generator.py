from datetime import datetime
from math import pi, cos, sin, floor

from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
from weasyprint.fonts import FontConfiguration
from cairosvg import svg2png


class ReportGenerator(object):
    def __init__(self, report_data, template_path, output_path='/tmp/'):
        """

        :param report_data:
        :param template_path:
        :param output_path:
        """
        self.report_data = report_data
        self.template_path = template_path
        self.output_path = output_path
        self.env = Environment(loader=FileSystemLoader('.'))

    def generate(self):
        """
        Build HTML file representing a report that consists of:
        1. Summary - all Dashboard cards (except lifecycle)
        2. Section per adapter - containing predefined saved queries, with the amount of results for their execution.
        3. Saved Views - a snippet of the entity table's first page, for each saved view (of both entities)
        A pdf file is generated on the basis of the created html and a matching stylesheet.

        :return: The name of the generated pdf file
        """
        report_template = self._get_template('axonius_report')
        section_template = self._get_template('report_section')
        card_template = self._get_template('report_card')

        now = datetime.now()
        sections = []
        # Add summary section containing dashboard panels, pre- and user-defined
        sections.append(section_template.render({'title': 'Summary', 'content': self._create_summary(card_template)}))
        if self.report_data.get('adapter_queries'):
            for adapter in self.report_data['adapter_queries']:
                sections.append(section_template.render({'title': adapter['name'],
                                                         'content': self._create_adapter(adapter['queries'])}))
        # Join all sections as the content of the report
        html_data = report_template.render({'date': now.strftime("%d/%m/%Y"), 'content': '\n'.join(sections)})

        timestamp = now.strftime("%d%m%Y-%H%M%S")
        temp_report_filename = f'{self.output_path}axonius-report_{timestamp}.pdf'
        with open(f'{self.output_path}axonius-report_{timestamp}.html', 'w') as file:
            file.write(html_data)
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

    def _create_summary(self, card_template):
        """
        Create HTML part for each of the dashboard predefined charts as well as those defined by user.

        :return:
        """
        pie_template = self._get_template('summary/pie_chart')
        pie_slice_template = self._get_template('summary/pie_slice')
        histogram_template = self._get_template('summary/histogram_chart')
        histogram_bar_template = self._get_template('summary/histogram_bar')

        summary_content = []
        if self.report_data.get('adapter_devices') and self.report_data['adapter_devices'].get('total_gross') \
                and self.report_data['adapter_devices'].get('total_net'):
            # Adding main summary card - the data discovery
            data_discovery_template = self._get_template('summary/data_discovery')
            summary_content.append(card_template.render({
                'title': 'Data Discovery',
                'class': 'full',
                'content': data_discovery_template.render({
                    'seen_count': self.report_data['adapter_devices']['total_gross'],
                    'unique_count': self.report_data['adapter_devices']['total_net']
                })}))

        if self.report_data.get('coverage'):
            # Adding cards with coverage of network roles
            for coverage_data in self.report_data['coverage']:
                coverage_pie_filename = "_".join(coverage_data["title"].split(" ")) + '.png'
                svg2png(
                    bytestring=self._create_coverage_pie(coverage_data['portion'], pie_template, pie_slice_template),
                    write_to=f'{self.output_path}{coverage_pie_filename}')
                summary_content.append(card_template.render({
                    'title': f'{coverage_data["title"]} Coverage',
                    'content': f'<img src="{coverage_pie_filename}">'
                }))

        if self.report_data.get('adapter_devices') and self.report_data['adapter_devices'].get('adapter_count'):
            # Adding card with histogram comparing amount of devices from each adapter
            summary_content.append(card_template.render({
                'title': 'Devices per Adapter',
                'content': self._create_adapter_histogram(histogram_template, histogram_bar_template)
            }))
        return '\n'.join(summary_content)

    def _create_coverage_pie(self, portion, pie_template, pie_slice_template):
        """
        Create a slice for the given portion, filled with a colour representing the quarter it is in
        and with the percentage as a text to present..
        Then, create a second slice with the remainder of the portion, coloured grey.

        :param portion:
        :param pie_template:
        :param pie_slice_template:
        :return:
        """
        colours = ['#D0011B', '#F6A623', '#4796E4', '#0FBC18']
        paths = self._calculate_pie_paths([1 - portion, portion])
        slices = [
            pie_slice_template.render({'path': paths[0], 'colour': '#DEDEDE'}),
            pie_slice_template.render({'path': paths[1], 'colour': colours[int(floor(portion * 4))],
                                       'text': f'{round(portion * 100)}%' if portion else '', 'x': 0.7, 'y': -0.1})
        ]
        return pie_template.render({
            'content': '\n'.join(slices)
        })

    def _calculate_pie_paths(self, portions):
        """
        Calculate each slice's path, which starts at previous slice's position, arches to the point calculated
        by adding current portion and ends in the center of the circle.

        :param portions:
        :return:
        """
        paths = []
        cumulative_portion = 0
        for portion in portions:
            (start_x, start_y) = self._calculate_coordinates(cumulative_portion)
            cumulative_portion += portion
            (end_x, end_y) = self._calculate_coordinates(cumulative_portion)
            paths.append(f'M {start_x} {start_y} A 1 1 0 {1 if portion > .5 else 0} 1 {end_x} {end_y} L 0 0')
        return paths

    def _calculate_coordinates(self, portion):
        """
        :param portion: Wanted percentage for the slice
        :return: (x, y) for the point on the circle that represents given portion
        """
        return (cos(2 * pi * portion), sin(2 * pi * portion))

    def _create_adapter_histogram(self, histogram_template, histogram_bar_template):
        """

        :param adapter_count:
        :param histogram_template:
        :param histogram_bar_template:
        :return:
        """
        bars = []
        adapters = self.report_data['adapter_devices']['adapter_count']
        adapters.sort(key=lambda x: x['count'], reverse=True)
        max = adapters[0]['count']
        for adapter in adapters[:6]:
            if not adapter.get('name') or not adapter.get('count'):
                continue
            width = 20 + ((180 * adapter['count']) / max)
            bars.append(histogram_bar_template.render({
                'name': adapter['name'], 'quantity': adapter['count'], 'width': width
            }))
        return histogram_template.render({'content': '\n'.join(bars),
                                          'remainder': f'+{len(adapters) - 6}' if len(adapters) > 6 else ''})

    def _create_adapter(self, queries):
        """
        Add a box for each query result count and name, with the appropriate colour if it's negative.

        :param queries:
        :return:
        """
        query_template = self._get_template('adapter/query_result_template')
        results = []
        for query in queries:
            results.append(query_template.render({
                'name': query['name'], 'count': query['count'],
                'colour': 'red' if query.get('negative', False) else 'orange'
            }))
        return '\n'.join(results)
