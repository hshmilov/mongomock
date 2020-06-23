import click

from .ax_dashboards import ax_dashboards


@click.group()
def cli():
    """The Axonius Commandline Interface"""


cli.add_command(ax_dashboards.ax_dashboards)
