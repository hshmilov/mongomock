import os

from jinja2 import Environment, FileSystemLoader

JINJA_ENV = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '../', 'templates', 'report')))


def get_template(template_name):
    """
    Get the template with requested name, expected to be found in self.template_path and have the extension 'html'
    :param template_name: Name of template file
    :return: The template object
    """
    return JINJA_ENV.get_template(f'{template_name}.html')


REPORTS_TEMPLATES = {
    'report': get_template('alert_report'),
    'calc_area': get_template('report_calc_area'),
    'header': get_template('report_header'),
    'second_header': get_template('report_second_header'),
    'table_section': get_template('report_tables_section'),
    'adapter_image': get_template('adapter_image'),
    'entity_name_url': get_template('entity_name_url'),
    'table': get_template('report_table'),
    'table_head': get_template('report_table_head'),
    'table_row': get_template('report_table_row'),
    'table_data': get_template('report_table_data')
}
