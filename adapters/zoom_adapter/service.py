import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from zoom_adapter.connection import ZoomConnection
from zoom_adapter.client_id import get_client_id
from zoom_adapter.consts import ZOOM_USER_TYPE, ZOOM_VERIFIED, ZOOM_DEFAULT_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class ScheduleMeeting(SmartJsonClass):
    host_video = Field(bool, 'Host Video')
    participants_video = Field(bool, 'Participants Video')
    audio_type = Field(str, 'Audio Type')
    join_before_host = Field(bool, 'Join Before Host')
    force_pmi_jbh_password = Field(bool, 'Force Pmi JBH Password')
    pstn_password_protected = Field(bool, 'Pstn Password Protected')
    use_pmi_for_scheduled_meetings = Field(bool, 'Use Pmi For Scheduled Meetings')
    use_pmi_for_instant_meetings = Field(bool, 'Use Pmi For Instant Meetings')
    require_password_for_scheduling_new_meetings = Field(bool, 'Require Password For Scheduling New Meetings')
    require_password_for_scheduled_meetings = Field(bool, 'Require Password For Scheduled Meetings')
    require_password_for_instant_meetings = Field(bool, 'Require Password For Instant Meetings')
    require_password_for_pmi_meetings = Field(str, 'Require Password For Pmi Meetings')


class Telephony(SmartJsonClass):
    third_party_audio = Field(bool, 'Third Party Audio')
    audio_conference_info = Field(str, 'Audio Conference Info')
    show_international_numbers_link = Field(bool, 'Show International Numbers Link')


class Feature(SmartJsonClass):
    meeting_capacity = Field(int, 'Meeting Capacity')
    large_meeting = Field(bool, 'Large Meeting')
    webinar = Field(bool, 'Webinar')
    cn_meeting = Field(bool, 'Cn Meeting')
    in_meeting = Field(bool, 'In Meeting')
    zoom_phone = Field(bool, 'Zoom Phone')


class Tsp(SmartJsonClass):
    call_out = Field(bool, 'Call Out')
    call_out_countries = ListField(str, 'Call Out Countries')
    show_international_numbers_link = Field(bool, 'Show International Numbers Link')


class EmailNotification(SmartJsonClass):
    jbh_reminder = Field(bool, 'Jbh Reminder')
    cancel_meeting_reminder = Field(bool, 'Cancel Meeting Reminder')
    alternative_host_reminder = Field(bool, 'Alternative Host Reminder')
    schedule_for_reminder = Field(bool, 'Schedule For Reminder')


class Recording(SmartJsonClass):
    local_recording = Field(bool, 'Local Recording')
    cloud_recording = Field(bool, 'Cloud Recording')
    record_speaker_view = Field(bool, 'Record Speaker View')
    record_gallery_view = Field(bool, 'Record Gallery View')
    record_audio_file = Field(bool, 'Record Audio File')
    save_chat_text = Field(bool, 'Save Chat Text')
    show_timestamp = Field(bool, 'Show Timestamp')
    recording_audio_transcript = Field(bool, 'Recording Audio Transcript')
    auto_recording = Field(str, 'Auto Recording')
    host_pause_stop_recording = Field(bool, 'Host Pause Stop Recording')
    auto_delete_cmr = Field(bool, 'Auto Delete Cmr')
    auto_delete_cmr_days = Field(int, 'Auto Delete Cmr Days')


class InMeeting(SmartJsonClass):
    e2e_encryption = Field(bool, 'E2E Encryption')
    chat = Field(bool, 'Chat')
    private_chat = Field(bool, 'Private Chat')
    auto_saving_chat = Field(bool, 'Auto Saving Chat')
    entry_exit_chime = Field(str, 'Entry Exit Chime')
    record_play_voice = Field(bool, 'Record Play Voice')
    feedback = Field(bool, 'Feedback')
    co_host = Field(bool, 'Co Host')
    data_center_regions = ListField(str, 'Data Center Regions')
    polling = Field(bool, 'Polling')
    attendee_on_hold = Field(bool, 'Attendee On Hold')
    annotation = Field(bool, 'Annotation')
    remote_control = Field(bool, 'Remote Control')
    non_verbal_feedback = Field(bool, 'Non Verbal Feedback')
    breakout_room = Field(bool, 'Breakout Room')
    remote_support = Field(bool, 'Remote Support')
    closed_caption = Field(bool, 'Closed Caption')
    group_hd = Field(bool, 'Group HD')
    virtual_background = Field(bool, 'Virtual Background')
    far_end_camera_control = Field(bool, 'Far End Camera Control')
    share_dual_camera = Field(bool, 'Share Dual Camera')
    waiting_room = Field(bool, 'Waiting Room')
    allow_live_streaming = Field(bool, 'Allow Live Streaming')
    workplace_by_facebook = Field(bool, 'Workplace By Facebook')
    custom_live_streaming_service = Field(bool, 'Custom Live Streaming Service')
    custom_service_instructions = Field(str, 'Custom Service Instructions')
    show_meeting_control_toolbar = Field(bool, 'Show Meeting Control Toolbar')


class ZoomAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UserAdapter):
        user_type = Field(str, 'User Type')
        timezone = Field(str, 'Timezone')
        last_client_version = Field(str, 'Last Client Version')
        pmi = Field(int, 'PMI')
        verified = Field(bool, 'Verified')
        im_groups = ListField(str, 'IM Groups')
        schedule_meeting = Field(ScheduleMeeting, 'Schedule Meeting')
        in_meeting = Field(InMeeting, 'In Meeting')
        email_notification = Field(EmailNotification, 'Email Notification')
        recording = Field(Recording, 'Recording')
        telephony = Field(Telephony, 'Telephony')
        feature = Field(Feature, 'Feature')
        tsp = Field(Tsp, 'Tsp')

    class MyDeviceAdapter(DeviceAdapter):
        protocol = Field(str, 'Protocol')
        encryption = Field(str, 'Encryption')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def get_connection(client_config):
        connection = ZoomConnection(domain=client_config['domain'],
                                    apikey=client_config['apikey'],
                                    verify_ssl=client_config['verify_ssl'],
                                    api_secret=client_config['api_secret'],
                                    https_proxy=client_config.get('https_proxy')
                                    )
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint: disable=arguments-differ
    @staticmethod
    def _query_users_by_client(key, data):
        with data:
            yield from data.get_user_list()

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_user(self, user_raw, groups_dict, im_groups_dict):
        try:
            user = self._new_user_adapter()
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('email') or '')
            user.first_name = user_raw.get('first_name')
            user.last_name = user_raw.get('last_name')
            user.username = (user_raw.get('first_name') or '') + ' ' + (user_raw.get('last_name') or '')
            user.mail = user_raw.get('email')
            user.user_created = parse_date(user_raw.get('created_at'))
            user.last_logon = parse_date(user_raw.get('last_login_time'))
            user.user_status = user_raw.get('status')
            user.user_department = user_raw.get('dept')
            user.pmi = user_raw.get('pmi') if isinstance(user_raw.get('pmi'), int) else None
            user.user_type = ZOOM_USER_TYPE.get(user_raw.get('type'))
            user.verified = ZOOM_VERIFIED.get(user_raw.get('verified'))
            user.timezone = user_raw.get('timezone')
            group_ids = user_raw.get('group_ids')
            if not isinstance(group_ids, list):
                group_ids = []
            for group_id in group_ids:
                if groups_dict.get(group_id):
                    user.groups.append(groups_dict.get(group_id).get('name'))
            im_group_ids = user_raw.get('im_group_ids')
            if not isinstance(im_group_ids, list):
                im_group_ids = []
            for im_group_id in im_group_ids:
                if im_groups_dict.get(im_group_id):
                    user.im_groups.append(im_groups_dict.get(im_group_id).get('name'))
            user.last_client_version = user_raw.get('last_client_version')
            try:
                settings_raw = user_raw.get('settings_raw')
                if not isinstance(settings_raw, dict):
                    settings_raw = {}
                schedule_meeting = settings_raw.get('schedule_meeting')
                if not isinstance(schedule_meeting, dict):
                    schedule_meeting = {}
                use_pmi_for_scheduled_meetings = schedule_meeting.get('use_pmi_for_scheduled_meetings')
                req_pas_4 = schedule_meeting.get('require_password_for_pmi_meetings')
                req_pas_3 = schedule_meeting.get('require_password_for_instant_meetings')
                req_pas_2 = schedule_meeting.get('require_password_for_scheduled_meetings')
                use_pmi_1 = schedule_meeting.get('use_pmi_for_instant_meetings')
                req_pas = schedule_meeting.get('require_password_for_scheduling_new_meetings')
                sch_ob = ScheduleMeeting(host_video=schedule_meeting.get('host_video'),
                                         participants_video=schedule_meeting.get('participants_video'),
                                         audio_type=schedule_meeting.get('audio_type'),
                                         join_before_host=schedule_meeting.get('join_before_host'),
                                         force_pmi_jbh_password=schedule_meeting.get('force_pmi_jbh_password'),
                                         pstn_password_protected=schedule_meeting.get('pstn_password_protected'),
                                         use_pmi_for_scheduled_meetings=use_pmi_for_scheduled_meetings,
                                         use_pmi_for_instant_meetings=use_pmi_1,
                                         require_password_for_scheduling_new_meetings=req_pas,
                                         require_password_for_scheduled_meetings=req_pas_2,
                                         require_password_for_instant_meetings=req_pas_3,
                                         require_password_for_pmi_meetings=req_pas_4)
                user.schedule_meeting = sch_ob
                in_meeting = settings_raw.get('in_meeting')
                if not isinstance(in_meeting, dict):
                    in_meeting = {}
                in_m_ob = InMeeting(e2e_encryption=in_meeting.get('e2e_encryption'),
                                    chat=in_meeting.get('chat'),
                                    private_chat=in_meeting.get('private_chat'),
                                    auto_saving_chat=in_meeting.get('auto_saving_chat'),
                                    entry_exit_chime=in_meeting.get('entry_exit_chime'),
                                    record_play_voice=in_meeting.get('record_play_voice'),
                                    feedback=in_meeting.get('feedback'),
                                    co_host=in_meeting.get('co_host'),
                                    data_center_regions=in_meeting.get('data_center_regions'),
                                    polling=in_meeting.get('polling'),
                                    attendee_on_hold=in_meeting.get('attendee_on_hold'),
                                    annotation=in_meeting.get('annotation'),
                                    remote_control=in_meeting.get('remote_control'),
                                    non_verbal_feedback=in_meeting.get('non_verbal_feedback'),
                                    breakout_room=in_meeting.get('breakout_room'),
                                    remote_support=in_meeting.get('remote_support'),
                                    closed_caption=in_meeting.get('closed_caption'),
                                    group_hd=in_meeting.get('group_hd'),
                                    virtual_background=in_meeting.get('virtual_background'),
                                    far_end_camera_control=in_meeting.get('far_end_camera_control'),
                                    share_dual_camera=in_meeting.get('share_dual_camera'),
                                    waiting_room=in_meeting.get('waiting_room'),
                                    allow_live_streaming=in_meeting.get('allow_live_streaming'),
                                    workplace_by_facebook=in_meeting.get('workplace_by_facebook'),
                                    custom_live_streaming_service=in_meeting.get('custom_live_streaming_service'),
                                    custom_service_instructions=in_meeting.get('custom_service_instructions'),
                                    show_meeting_control_toolbar=in_meeting.get('show_meeting_control_toolbar'))
                user.in_meeting = in_m_ob
                email_notification = settings_raw.get('email_notification')
                if not isinstance(email_notification, dict):
                    email_notification = {}
                aleter_hosts_1 = email_notification.get('alternative_host_reminder')
                em_ob = EmailNotification(jbh_reminder=email_notification.get('jbh_reminder'),
                                          cancel_meeting_reminder=email_notification.get('cancel_meeting_reminder'),
                                          alternative_host_reminder=aleter_hosts_1)
                user.email_notification = em_ob

                recording = settings_raw.get('recording')
                if not isinstance(recording, dict):
                    recording = {}
                rec_ob = Recording(local_recording=recording.get('local_recording'),
                                   cloud_recording=recording.get('cloud_recording'),
                                   record_speaker_view=recording.get('record_speaker_view'),
                                   record_gallery_view=recording.get('record_gallery_view'),
                                   record_audio_file=recording.get('record_audio_file'),
                                   save_chat_text=recording.get('save_chat_text'),
                                   show_timestamp=recording.get('show_timestamp'),
                                   recording_audio_transcript=recording.get('recording_audio_transcript'),
                                   auto_recording=recording.get('auto_recording'),
                                   host_pause_stop_recording=recording.get('host_pause_stop_recording'),
                                   auto_delete_cmr=recording.get('auto_delete_cmr'),
                                   auto_delete_cmr_days=recording.get('auto_delete_cmr_days'))
                user.recording = rec_ob
                telephony = settings_raw.get('telephony')
                if not isinstance(telephony, dict):
                    telephony = {}
                show_1 = telephony.get('show_international_numbers_link')
                tele_ob = Telephony(third_party_audio=telephony.get('third_party_audio'),
                                    audio_conference_info=telephony.get('audio_conference_info'),
                                    show_international_numbers_link=show_1)
                user.telephony = tele_ob

                feature = settings_raw.get('feature')
                if not isinstance(feature, dict):
                    feature = {}
                feat_ob = Feature(meeting_capacity=feature.get('meeting_capacity'),
                                  large_meeting=feature.get('large_meeting'),
                                  webinar=feature.get('webinar'),
                                  cn_meeting=feature.get('cn_meeting'),
                                  in_meeting=feature.get('in_meeting'),
                                  zoom_phone=feature.get('zoom_phone'))
                user.feature = feat_ob

                tsp = settings_raw.get('tsp')
                if not isinstance(tsp, dict):
                    tsp = {}
                call_out_countries = tsp.get('call_out_countries') \
                    if isinstance(tsp.get('call_out_countries'), list) else None
                tsp_ob = Tsp(call_out=tsp.get('call_out'),
                             call_out_countries=call_out_countries,
                             show_international_numbers_link=tsp.get('show_international_numbers_link'))
                user.tsp = tsp_ob
            except Exception:
                logger.exception(f'Problem with settting for {user_raw}')
            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Zoom user for {user_raw}')
            return None

    def _parse_users_raw_data(self, users_raw_data):
        for user_raw, groups_dict, im_groups_dict in users_raw_data:
            user = self._create_user(user_raw, groups_dict, im_groups_dict)
            if user:
                yield user

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.hostname = device_raw.get('name')
            device.add_nic(ips=[device_raw.get('ip')])
            device.protocol = device_raw.get('protocol')
            device.encryption = device_raw.get('encryption')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Zoom Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @staticmethod
    def _clients_schema():
        """
        The schema ZoomAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Zoom Domain',
                    'type': 'string',
                    'default': ZOOM_DEFAULT_DOMAIN
                },
                {
                    'name': 'apikey',
                    'type': 'string',
                    'title': 'JWT API Key'
                },
                {
                    'name': 'api_secret',
                    'type': 'string',
                    'format': 'password',
                    'title': 'JWT API Secret'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'verify_ssl',
                'api_secret',
                'apikey'
            ],
            'type': 'array'
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement, AdapterProperty.Agent]
