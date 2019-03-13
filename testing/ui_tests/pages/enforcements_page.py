import time
import os

from ui_tests.pages.entities_page import EntitiesPage


class Period:
    EveryDiscovery = 'all_period'
    Daily = 'daily_period'
    Weekly = 'weekly_period'


class Trigger:
    NewEntities = 'New entities were added to results'
    PreviousEntities = 'Previous entities were subtracted from results'
    Above = 'The number of results is above...'
    Below = 'The number of results is below...'


class Action:
    SendMail = 'Send Mail'
    PushNotification = 'Push System Notification'
    IsolateCB = 'Isolate in CarbonBlack'
    Syslog = 'Send to Syslog System'
    Tag = 'Add Tag'
    DeployWindows = 'Deploy on Windows Device'
    ScanQualys = 'Add to Qualys'
    ScanTenable = 'Add to Tenable'


class ActionCategory:
    Deploy = 'Deploy Software'
    Notify = 'Notify'
    Isolate = 'Isolate Device in EDR'
    Utils = 'Axonius Utilities'
    Scan = 'Add Device to VA Scan'


class EnforcementsPage(EntitiesPage):
    ENFORCEMENT_NAME_ID = 'enforcement_name'
    NEW_ENFORCEMENT_BUTTON = '+ New Enforcement'
    TRIGGER_CONTAINER_CSS = '.x-trigger'
    TRIGGER_CONF_CONTAINER_CSS = '.x-trigger-config'
    MAIN_ACTION_TEXT = 'main action'
    SUCCESS_ACTIONS_TEXT = 'success actions'
    FAILURE_ACTIONS_TEXT = 'failure actions'
    POST_ACTIONS_TEXT = 'post actions'
    ACTION_LIBRARY_CONTAINER_CSS = '.x-action-library'
    ACTION_CONF_CONTAINER_CSS = '.x-action-config'
    ACTION_RESULT_CONTAINER_CSS = '.x-action-result'
    ACTION_NAME_ID = 'action-name'
    ACTION_BY_NAME_XPATH = '//div[@class=\'x-text-box\' and child::div[text()=\'{action_name}\']]'
    SELECT_VIEW_ENTITY_CSS = '.base-query .x-select-symbol .x-select-trigger'
    SELECT_VIEW_NAME_CSS = '.base-query .query-name .x-select-trigger'
    SELECT_SAVED_VIEW_TEXT_CSS = 'div.trigger-text'
    ENFORCEMENTS_CHECKBOX = 'div.x-checkbox-container'
    ABOVE_INPUT_CSS = '.config .config-item .above'
    BELOW_INPUT_CSS = '.config .config-item .below'
    EDIT_ENFORCEMENT_XPATH = '//div[@title=\'{enforcement_name}\']'
    SEND_AN_EMAIL = 'Send an Email'
    DISABLED_ACTION_XPATH = '//div[contains(@class, \'md-list-item-content\')]//div[@class=\'x-title disabled\' ' \
                            'and .//text()=\'{action_name}\']'
    TASK_RESULT_CSS = '.x-action-result .x-summary div:nth-child({child_count})'
    TASK_RESULT_SUCCESS_CSS = TASK_RESULT_CSS.format(child_count=1)
    TASK_RESULT_FAILURE_CSS = TASK_RESULT_CSS.format(child_count=3)

    @property
    def url(self):
        return f'{self.base_url}/enforcements'

    @property
    def root_page_css(self):
        return 'li#enforcements.x-nav-item'

    def find_checkbox_by_label(self, text):
        return self.driver.find_element_by_xpath(self.CHECKBOX_XPATH_TEMPLATE.format(label_text=text))

    def click_new_enforcement(self):
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()
        self.wait_for_element_present_by_text(self.NEW_ENFORCEMENT_BUTTON)
        self.find_new_enforcement_button().click()
        self.wait_for_element_present_by_css(self.TRIGGER_CONTAINER_CSS)

    def find_new_enforcement_button(self):
        return self.get_button(self.NEW_ENFORCEMENT_BUTTON)

    def fill_enforcement_name(self, name):
        self.fill_text_field_by_element_id(self.ENFORCEMENT_NAME_ID, name)

    def add_send_email(self):
        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_element_present_by_css(self.ACTION_LIBRARY_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        self.find_element_by_text(ActionCategory.Notify).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.SendMail).click()

    def tag_entities(self, name, tag, new=False):
        self.wait_for_element_present_by_css(self.ACTION_CONF_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        if new:
            self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        self.fill_text_field_by_element_id('tag_name', tag)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def add_tag_entities(self, name='Special Tag Action', tag='Special', action_cond=MAIN_ACTION_TEXT):
        self.find_element_by_text(action_cond).click()
        self.wait_for_element_present_by_css(self.ACTION_LIBRARY_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        self.find_element_by_text(ActionCategory.Utils).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.Tag).click()
        self.tag_entities(name, tag, new=True)

    def change_tag_entities(self, name='Special Tag Action', tag='Special'):
        self.driver.find_element_by_xpath(self.ACTION_BY_NAME_XPATH.format(action_name=name)).click()
        self.tag_entities(name, tag)

    def fill_tag_all_text(self, tag_text):
        self.fill_text_field_by_element_id('tagAllName', tag_text)

    def fill_tag_new_text(self, tag_text):
        self.fill_text_field_by_element_id('tagNew', tag_text)

    def add_cb_isolate(self, name='Special Isolate Action', action_cond=MAIN_ACTION_TEXT):
        self.add_generic_action(ActionCategory.Isolate, Action.IsolateCB, name, action_cond)

    def add_generic_action(self, action_category, action_type, name, action_cond=MAIN_ACTION_TEXT):
        self.find_element_by_text(action_cond).click()
        self.wait_for_element_present_by_css(self.ACTION_LIBRARY_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        self.find_element_by_text(action_category).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(action_type).click()
        self.wait_for_element_present_by_css(self.ACTION_CONF_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def open_action_category(self, category_name):
        self.find_element_by_text(category_name).click()

    def find_disabled_action(self, action_name):
        return self.driver.find_element_by_xpath(self.DISABLED_ACTION_XPATH.format(action_name=action_name))

    def find_missing_email_server_notification(self):
        return self.find_element_by_text('In order to send alerts through mail, configure it under settings')

    def check_enforcement_checkbox(self, text):
        self.find_element_by_text(text).click()

    def check_scheduling(self):
        self.check_enforcement_checkbox('Add Scheduling')

    def check_conditions(self):
        self.check_enforcement_checkbox('Add Conditions')

    def check_new(self):
        self.check_enforcement_checkbox(Trigger.NewEntities)

    def check_previous(self):
        self.check_enforcement_checkbox(Trigger.PreviousEntities)

    def check_above(self):
        self.check_enforcement_checkbox(Trigger.Above)

    def check_below(self):
        self.check_enforcement_checkbox(Trigger.Below)

    def check_new_entities(self):
        self.check_enforcement_checkbox('Run on added entities only')

    def add_push_system_notification(self, name='Special Push Notification'):
        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_element_present_by_css(self.ACTION_LIBRARY_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        self.find_element_by_text(ActionCategory.Notify).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.PushNotification).click()
        self.wait_for_element_present_by_css(self.ACTION_CONF_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        self.fill_action_name(name)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def fill_action_name(self, name):
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)

    def add_notify_syslog(self, name='Special Syslog Notification', action_cond=MAIN_ACTION_TEXT, severity='warning'):
        # 'warning' by default, because our syslog doesn't like logs sent using "INFO"
        # It is an issue with our syslog's configuration, and it's not worth the time fixing

        self.find_element_by_text(action_cond).click()
        self.wait_for_element_present_by_css(self.ACTION_LIBRARY_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        self.find_element_by_text(ActionCategory.Notify).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.Syslog).click()
        self.wait_for_element_present_by_css(self.ACTION_CONF_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        self.select_option_without_search(f'{self.ACTION_CONF_CONTAINER_CSS} .x-dropdown.x-select',
                                          self.DROPDOWN_SELECTED_OPTION_CSS, severity)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def add_deploy_software(self, name='Deploy Special Software'):
        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_element_present_by_css(self.ACTION_LIBRARY_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        self.find_element_by_text(ActionCategory.Deploy).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.DeployWindows).click()
        self.wait_for_element_present_by_css(self.ACTION_CONF_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        exe_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../uploaded_files/test_binary.exe'))
        self.upload_file_by_id('executable', open(exe_path, 'rb').read(), is_bytes=True)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def select_trigger(self):
        self.driver.find_element_by_css_selector(self.TRIGGER_CONTAINER_CSS).click()
        self.wait_for_element_present_by_css(self.TRIGGER_CONF_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)

    def save_trigger(self):
        self.click_button(self.SAVE_BUTTON, scroll_into_view_container=self.TRIGGER_CONF_CONTAINER_CSS,
                          context=self.driver.find_element_by_css_selector(self.TRIGGER_CONF_CONTAINER_CSS))

    def select_saved_view(self, text, entity='Devices'):
        self.select_option_without_search(self.SELECT_VIEW_ENTITY_CSS, self.DROPDOWN_SELECTED_OPTION_CSS, entity)
        self.select_option(self.SELECT_VIEW_NAME_CSS, self.DROPDOWN_TEXT_BOX_CSS, self.DROPDOWN_SELECTED_OPTION_CSS,
                           text)

    def save_action(self):
        self.click_button(self.SAVE_BUTTON, scroll_into_view_container=self.ACTION_CONF_CONTAINER_CSS,
                          context=self.driver.find_element_by_css_selector(self.ACTION_CONF_CONTAINER_CSS))

    def click_save_button(self):
        self.click_button('Save & Exit')

    def click_run_button(self):
        self.click_button('Save & Run', partial_class=True)

    def click_tasks_button(self):
        self.click_button('View Tasks', partial_class=True)

    def select_all_enforcements(self):
        self.driver.find_element_by_css_selector(self.ENFORCEMENTS_CHECKBOX).click()

    def remove_selected_enforcements(self):
        self.find_element_by_text('Remove').click()

    def choose_period(self, period):
        self.driver.find_element_by_id(period).click()

    def fill_above_value(self, value):
        self.fill_text_field_by_css_selector(self.ABOVE_INPUT_CSS, value)

    def get_above_value(self):
        return self.driver.find_element_by_css_selector(self.ABOVE_INPUT_CSS).get_attribute('value')

    def fill_below_value(self, value):
        self.fill_text_field_by_css_selector(self.BELOW_INPUT_CSS, value)

    def edit_enforcement(self, enforcement_name):
        self.driver.find_element_by_xpath(self.EDIT_ENFORCEMENT_XPATH.format(enforcement_name=enforcement_name)).click()

    def get_saved_query_text(self):
        return self.driver.find_element_by_css_selector(self.SELECT_SAVED_VIEW_TEXT_CSS).get_attribute('title')

    def assert_screen_is_restricted(self):
        self.switch_to_page_allowing_failure()
        self.find_element_by_text('You do not have permission to access the Enforcements screen')
        self.click_ok_button()

    def create_basic_enforcement(self, enforcement_name, enforcement_view, schedule=True):
        self.switch_to_page()
        # for some reason, this switch_to_page doesn't work from here sometimes
        time.sleep(1)
        self.switch_to_page()
        self.click_new_enforcement()
        self.fill_enforcement_name(enforcement_name)
        self.select_trigger()
        if schedule:
            self.check_scheduling()
        self.select_saved_view(enforcement_view)
        self.save_trigger()

    def create_notifying_enforcement(self,
                                     enforcement_name,
                                     enforcement_view,
                                     new=True,
                                     previous=True,
                                     above=0,
                                     below=0):

        self.create_basic_enforcement(enforcement_name, enforcement_view)
        self.select_trigger()
        self.check_conditions()
        if new:
            self.check_new()
        if previous:
            self.check_previous()
        if above:
            self.check_above()
            self.fill_above_value(above)
        if below:
            self.check_below()
            self.fill_below_value(below)
        self.save_trigger()

        self.add_push_system_notification(enforcement_name)
        self.click_save_button()
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()

    def create_outputting_notification_above(self, alert_name, alert_query, above):
        self.create_notifying_enforcement(alert_name,
                                          alert_query,
                                          new=False,
                                          previous=False,
                                          above=above,
                                          below=0)

    def create_outputting_notification_below(self, alert_name, alert_query, below):
        self.create_notifying_enforcement(alert_name,
                                          alert_query,
                                          new=False,
                                          previous=False,
                                          above=0,
                                          below=below)

    def create_deploying_enforcement(self, enforcement_name, enforcement_view):
        self.create_basic_enforcement(enforcement_name, enforcement_view)
        self.add_deploy_software(enforcement_name)
        self.click_save_button()
        self.wait_for_table_to_load()

    def add_deploying_consequences(self, enforcement_name, success_tag_name, failure_tag_name, failure_isolate_name):
        self.edit_enforcement(enforcement_name)
        self.add_tag_entities(name=success_tag_name, tag='Specially Deployed', action_cond=self.SUCCESS_ACTIONS_TEXT)
        self.add_cb_isolate(name=failure_isolate_name, action_cond=self.FAILURE_ACTIONS_TEXT)
        self.add_tag_entities(name=failure_tag_name, tag='Missing Special Deploy',
                              action_cond=self.FAILURE_ACTIONS_TEXT)
        self.click_save_button()
        self.wait_for_table_to_load()

    def is_severity_selected(self, severity):
        return self.driver.find_element_by_css_selector(severity).is_selected()

    def is_period_selected(self, period):
        return self.driver.find_element_by_id(period).is_selected()

    def is_action_selected(self, action):
        return self.find_element_by_text(action) is not None

    def is_trigger_selected(self, trigger):
        element = self.find_checkbox_container_by_label(trigger)
        return element.get_attribute('class') == 'x-checkbox grid-span2 x-checked'

    def find_checkbox_container_by_label(self, label_text):
        return self.driver.find_element_by_xpath(self.DIV_BY_LABEL_TEMPLATE.format(label_text=label_text))

    def select_task_action(self, name):
        self.find_element_by_text(name).click()
        self.wait_for_element_present_by_css(self.ACTION_RESULT_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)

    def find_task_action_success(self, name):
        self.select_task_action(name)
        assert self.find_element_by_text('Entities Succeeded')
        return self.driver.find_element_by_css_selector(self.TASK_RESULT_SUCCESS_CSS)

    def find_task_action_failure(self, name):
        self.select_task_action(name)
        assert self.find_element_by_text('Entities Failed')
        return self.driver.find_element_by_css_selector(self.TASK_RESULT_FAILURE_CSS)
