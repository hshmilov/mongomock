import json
import logging
from typing import Dict, List

import webscan_adapter.scanners.cmseek.cmseekdb.basic as cmseek
import webscan_adapter.scanners.cmseek.cmseekdb.core as core
from webscan_adapter.scanners.service_scanner import ServiceScanner
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass


logger = logging.getLogger(f'axonius.{__name__}')


class Plugin(SmartJsonClass):
    name = Field(str, 'Name')
    version = Field(str, 'Version')


class CMS(SmartJsonClass):
    cms_id = Field(str, 'CMS Id')
    cms_name = Field(str, 'CMS Name')
    cms_version = Field(str, 'CMS Version')
    cms_plugins = ListField(Plugin, 'CMS Plugins')
    cms_themes = ListField(Plugin, 'CMS Themes')
    detection_param = Field(str, 'CMS Detection Param')
    cms_license = Field(str, 'License')
    cms_changelog = Field(str, 'Changelog')
    cms_readme = Field(str, 'Readme file')
    cms_user_registration = Field(str, 'Registration URL')


class CMSScanner(ServiceScanner):
    """
    Parse CMS data from http server
    """
    USER_AGENT = 'Axonius-scanner'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def parse_plugins(plugins_data: list) -> List[Dict]:
        """
        Parse cmseek plugins data
        :param plugins_data: plugins to parse
        :return: parsed plugins dict
        """
        plugins = []
        for plugin in plugins_data:
            try:
                plugin_version = None
                if 'Version' in plugin:
                    plugin_name, plugin_version = plugin.split('Version')
                else:
                    plugin_name = plugin
                if plugin_name:
                    plugins.append({
                        'name': plugin_name.strip() if plugin_name else None,
                        'version': plugin_version.strip() if plugin_version else None
                    })
            except Exception:
                logger.exception(f'Error parsing {plugin}')
        return plugins

    @staticmethod
    def handle_results(results: Dict) -> Dict:
        """
        Parse cmseek results
        :param results: rersults to parse
        :return: parsed cmseek results dict
        """
        plugins_data = results.get('wp_plugins').split(',') if results.get('wp_plugins') else []
        results['wp_plugins'] = CMSScanner.parse_plugins(plugins_data)
        themes_data = results.get('wp_themes').split(',') if results.get('wp_themes') else []
        results['wp_themes'] = CMSScanner.parse_plugins(themes_data)
        return results

    def scan(self):
        """
        Scan url using cmscan
        :param url: url/domain for scanning
        :return: scan results data
        Notes:
            I know its not the best solution,
            but cmscan code is written for command line use and not as a library,
            the best option is to get the scan output from 'log' global variable'
            Of course its not thread safe. but for now I'm not gonna refactor and maintain their whole code.
        """
        with cmseek.lock:
            cmseek.batch_mode = True
            cmseek.redirect_conf = '1'
            cmseek.log = '{"url":"","last_scanned":"","detection_param":"","cms_id":"","cms_name":"","cms_url":""}'
            target = cmseek.process_url(self.url)
            core.main_proc(target, self.USER_AGENT)
            results = json.loads(cmseek.log)
            self.results = self.handle_results(results)
            return self.results

    def parse(self, device: DeviceAdapter):
        """
        Parse cmscan results data
        :param data: results data
        :param device: adapter device
        :return: None
        """
        if not self.results:
            return
        data = self.results
        plugins = data.get('wp_plugins') or []
        plugins_data = []
        for plugin in plugins:
            try:
                if plugin.get('name'):
                    plugins_data.append(Plugin(name=plugin.get('name'),
                                               version=plugin.get('version')))
            except Exception:
                logger.exception('Cannot add plugin')

        themes = data.get('wp_themes') or []
        themes_data = []
        for theme in themes:
            try:
                themes_data.append(Plugin(name=theme.get('name'),
                                          version=theme.get('version')))
            except Exception:
                logger.exception('Cannot add theme')

        cms = CMS(cms_id=data.get('cms_id'),
                  cms_name=data.get('cms_name'),
                  detection_param=data.get('detection_param'),
                  cms_readme=data.get('readme_file'),
                  cms_license=data.get('license_file'),
                  cms_version=data.get('cms_version'),
                  cms_changelog=data.get('changelog_file'),
                  cms_user_registration=data.get('user_registration'),
                  cms_plugins=plugins_data,
                  cms_themes=themes_data)
        device.cms = cms
        if data.get('wp_users'):
            users = data.get('wp_users').split(',')
            for user in users:
                device.add_users(username=user)
