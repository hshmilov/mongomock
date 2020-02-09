import logging

from axonius.consts import plugin_consts
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.mixins.triggerable import Triggerable, RunIdentifier
from axonius.plugin_base import PluginBase
from axonius.utils.files import get_local_config_file
from compliance.aws_cis.aws_cis import AWSCISGenerator

logger = logging.getLogger(f'axonius.{__name__}')


class ComplianceService(Triggerable, PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=plugin_consts.COMPLIANCE_PLUGIN_NAME, *args, **kwargs)

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name not in ['execute', 'execute_force']:
            raise RuntimeError('Job name is wrong')

        try:
            if job_name == 'execute_force' or self.should_cloud_compliance_run():
                logger.info(f'Running Compliance Report..')
                self.run_compliance_report()
            else:
                logger.info(f'Cloud compliance is not enabled, not running')
                return False
        except Exception:
            logger.exception(f'Exception in running compliance report')
        return ''

    @staticmethod
    def run_compliance_report():
        aws_cis_generator = AWSCISGenerator()
        aws_cis_generator.generate()

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.PreCorrelation
