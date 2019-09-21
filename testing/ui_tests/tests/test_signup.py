from collections import namedtuple

from axonius.consts.gui_consts import (Signup, SIGNUP_TEST_COMPANY_NAME)
from ui_tests.tests.ui_consts import (LOGGED_IN_MARKER, VALID_EMAIL, NEW_PASSWORD, INCORRECT_PASSWORD)
from ui_tests.pages.signup_page import SignupPage
from ui_tests.tests.ui_test_base import TestBase

Field = namedtuple('Field', 'id good_expressions bad_expressions')
Expression = namedtuple('Expression', 'value expected')


class TestSignup(TestBase):
    fields = [
        Field(id='companyName',
              good_expressions=[
                  Expression(SIGNUP_TEST_COMPANY_NAME, SignupPage.NONE_ERROR_MSG)
              ],
              bad_expressions=[
                  Expression('', SignupPage.FIELDS_ERROR_MESSAGES['companyName'])
              ]),
        Field(id='contactEmail',
              good_expressions=[
                  Expression(VALID_EMAIL, SignupPage.NONE_ERROR_MSG)
              ],
              bad_expressions=[
                  Expression('a', SignupPage.CONTACT_EMAIL_ERROR_MSG),
                  Expression('c', SignupPage.CONTACT_EMAIL_ERROR_MSG),
              ]),
        Field(id='newPassword',
              good_expressions=[
                  Expression(NEW_PASSWORD, SignupPage.NONE_ERROR_MSG)
              ],
              bad_expressions=[
                  Expression('', SignupPage.FIELDS_ERROR_MESSAGES['newPassword'])
              ]),
        Field(id='confirmNewPassword',
              good_expressions=[
                  Expression(NEW_PASSWORD, SignupPage.NONE_ERROR_MSG)
              ],
              bad_expressions=[
                  Expression('', SignupPage.FIELDS_ERROR_MESSAGES['confirmNewPassword'])
              ])
    ]

    def check_submit_button_disabled(self):
        return self.signup_page.is_element_disabled(self.signup_page.get_save_button())

    def restore_pre_signup_state(self):
        if LOGGED_IN_MARKER.is_file():
            LOGGED_IN_MARKER.unlink()
        self.axonius_system.gui.get_signup_collection().drop()

    def check_field_validations(self, field_id, good_expressions, bad_expressions):
        # helping variables
        good_expression = good_expressions[0].value
        no_error = good_expressions[0].expected
        # test list of bad expression and the responding error
        for expression in bad_expressions:
            # focus on field
            self.signup_page.focus_on_element(field_id)
            # check for not triggering the validation while typing
            self.signup_page.fill_text_field_by_element_id(field_id, expression.value)
            # check for error msg - expected to find no error
            assert self.signup_page.get_error_msg() == no_error
            # focus out to check if error massage exist
            self.signup_page.blur_on_element(field_id)
            # check if validation occur while focus out
            assert self.signup_page.get_error_msg() == expression.expected
            # submit button should be disabled
            assert self.check_submit_button_disabled()

        # reset field error
        self.signup_page.fill_text_field_by_element_id(field_id, good_expression)
        self.signup_page.blur_on_element(field_id)
        # check for error msg - expected to find no error
        assert self.signup_page.get_error_msg() == no_error

        # test list of good expression and not triggering an error
        for expression in good_expressions:
            # focus on field
            self.signup_page.focus_on_element(field_id)
            # check for not triggering the validation while typing
            self.signup_page.fill_text_field_by_element_id(field_id, expression.value)
            self.signup_page.blur_on_element(field_id)
            # check if no error exist while focus out
            assert self.signup_page.get_error_msg() == expression.expected

        # at this point the field will be filled with the last good expression value
        # and no error should be exist
        assert self.signup_page.get_error_msg() == no_error

    def test_signup(self):
        self.settings_page.switch_to_page()
        self.login_page.logout()
        self.restore_pre_signup_state()
        self.login_page.refresh()
        self.signup_page.wait_for_signup_page_to_load()

        for field in self.fields:
            self.check_field_validations(field.id, field.good_expressions, field.bad_expressions)

        # test identical password validation
        # enter fake password
        self.signup_page.fill_text_field_by_element_id(self.signup_page.CONFIRM_PASSWORD, INCORRECT_PASSWORD)
        # try to save the form - expect validation error
        self.signup_page.save_form()
        assert self.signup_page.get_error_msg() == self.signup_page.PASSWORDS_DONT_MATCH_MESSAGE
        # test submit button state
        # submit button should be disabled
        assert self.check_submit_button_disabled()
        # get beck to normal state step by step
        self.signup_page.fill_text_field_by_element_id(self.signup_page.CONFIRM_PASSWORD, NEW_PASSWORD[:-1])
        # submit button should be disabled
        assert self.check_submit_button_disabled()

        self.signup_page.fill_text_field_by_element_id(self.signup_page.CONFIRM_PASSWORD, NEW_PASSWORD)
        # submit button should be enabled
        assert not self.check_submit_button_disabled()

        self.signup_page.fill_text_field_by_element_id(self.signup_page.CONFIRM_PASSWORD, NEW_PASSWORD + '_test')
        # submit button should be disabled
        assert self.check_submit_button_disabled()

        self.signup_page.fill_text_field_by_element_id(self.signup_page.CONFIRM_PASSWORD, NEW_PASSWORD)
        # submit button should be enabled
        assert not self.check_submit_button_disabled()

        self.signup_page.fill_text_field_by_element_id(self.signup_page.CONTACT_EMAIL, '')

        # try to save the form
        self.signup_page.save_form()
        assert self.signup_page.get_error_msg() == self.signup_page.CONTACT_EMAIL_ERROR_MSG

        self.signup_page.fill_text_field_by_element_id(self.signup_page.CONTACT_EMAIL, VALID_EMAIL)
        # try to save the form
        self.signup_page.save_form()
        self.login_page.wait_for_login_page_to_load()

        signup_data = self.axonius_system.gui.get_signup_collection().find_one()
        # if this one changes - we might need to update integration with chef
        assert signup_data[Signup.CompanyField] == SIGNUP_TEST_COMPANY_NAME

        self.login_page.login(username='admin', password=NEW_PASSWORD)
        self.dashboard_page.find_trial_remainder_banner(30)
        self.settings_page.switch_to_page()

        self.login_page.logout()
        self.restore_pre_signup_state()
        self.login_page.refresh()
        self.signup_page.fill_signup_with_defaults_and_save()
