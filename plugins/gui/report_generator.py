from datetime import datetime
from math import pi, cos, sin, ceil

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
        Builds HTML file representing a report that consists of:
        1. Summary - all Dashboard cards (except lifecycle)
        2. Section per adapter - containing predefined saved queries, with the amount of results for their execution.
        3. Saved Views - a snippet of the entity table's first page, for each saved view (of both entities)
        A pdf file is generated on the basis of the created html and a matching stylesheet.

        :return: The name of the generated pdf file
        """
        report_template = self._get_template('axonius_report')
        section_template = self._get_template('report_section')

        now = datetime.now()
        html_data = report_template.render({
            'date': now.strftime("%d/%m/%Y"),
            'content': section_template.render({
                'title': 'Summary',
                'content': '\n'.join(self._create_summary())
            })
        })

        timestamp = now.strftime("%d%m%Y-%H%M%S")
        temp_report_filename = f'{self.output_path}axonius-report_{timestamp}.pdf'
        open(f'{self.output_path}axonius-report_{timestamp}.html', 'w').write(html_data)
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
        card_template = self._get_template('summary/card')
        data_discovery_template = self._get_template('summary/data_discovery')
        pie_template = self._get_template('summary/pie_chart')
        pie_slice_template = self._get_template('summary/pie_slice')

        summary_content = []
        # Adding main summary card - the data discovery
        summary_content.append(card_template.render({
            'title': 'Data Discovery',
            'class': 'full',
            'content': data_discovery_template.render({
                'seen_count': self.report_data['adapter_devices']['total_gross'],
                'unique_count': self.report_data['adapter_devices']['total_net']
            })}))
        # Adding remaining summary cards
        for coverage_data in self.report_data['coverage']:
            # open(f'{coverage_pie_file}.svg', 'w').write(
                # self._create_coverage_pie(coverage_data['portion'], pie_template, pie_slice_template))
            coverage_pie_filename = "_".join(coverage_data["title"].split(" ")) + '.png'
            svg2png(bytestring=self._create_coverage_pie(coverage_data['portion'], pie_template, pie_slice_template),
                    write_to=f'{self.output_path}{coverage_pie_filename}')
            summary_content.append(card_template.render({
                'title': f'{coverage_data["title"]} Coverage',
                'content': f'<img src="{coverage_pie_filename}">'
            }))
        return summary_content

    def _create_coverage_pie(self, portion, pie_template, pie_slice_template):
        """

        :param index:
        :return:
        """
        colours = ['', '#D0011B', '#F6A623', '#4796E4', '#0FBC18']
        paths = self._calculate_pie_paths([1 - portion, portion])
        slices = [
            pie_slice_template.render({'path': paths[0], 'colour': '#DEDEDE'}),
            pie_slice_template.render({'path': paths[1], 'colour': colours[ceil(portion * 4)],
                                       'text': f'{round(portion * 100)}%' if portion else '', 'x': 0.7, 'y': -0.1})
        ]
        return pie_template.render({
            'content': ''.join(slices)
        })

    def _calculate_pie_paths(self, portions):
        paths = []
        cumulative_portion = 0
        for portion in portions:
            (start_x, start_y) = self._calculate_coordinates(cumulative_portion)
            cumulative_portion += portion
            (end_x, end_y) = self._calculate_coordinates(cumulative_portion)
            paths.append(f'M {start_x} {start_y} A 1 1 0 {1 if portion > .5 else 0} 1 {end_x} {end_y} L 0 0')
        return paths

    def _calculate_coordinates(self, portion):
        return (cos(2 * pi * portion), sin(2 * pi * portion))
