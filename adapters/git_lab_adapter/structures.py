from datetime import datetime

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.utils.parsing import format_ip, format_ip_raw


class Project(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')


class Group(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')


class Statistics(SmartJsonClass):
    commit_count = Field(int, 'Commit Count')
    storage_size = Field(int, 'Storage Size')
    repository_size = Field(int, 'Repository Size')
    wiki_size = Field(int, 'Wiki Size')
    lfs_objects_size = Field(int, 'LFS Objects Size')
    job_artifacts_size = Field(int, 'Jobs Artifacts Size')
    packages_size = Field(int, 'Packages Size')
    snippets_size = Field(int, 'Snippets Size')


class Namespace(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')
    path = Field(str, 'Path')
    kind = Field(str, 'Kind')
    full_path = Field(str, 'Full Path')


class VulnerabilityIdentifier(SmartJsonClass):
    external_type = Field(str, 'External Type')
    external_id = Field(str, 'External ID')
    name = Field(str, 'Name')
    url = Field(str, 'URL')


class Dependency(SmartJsonClass):
    package_name = Field(str, 'Package Name')
    version = Field(str, 'Version')


class Location(SmartJsonClass):
    file = Field(str, 'File')
    dependency = Field(Dependency, 'Dependency')


class VulnerabilityFinding(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')
    severity = Field(str, 'Severity')
    confidence = Field(str, 'Confidence')
    identifiers = ListField(VulnerabilityIdentifier, 'Identifiers')
    description = Field(str, 'Description')
    solution = Field(str, 'Solution')
    location = Field(str, 'File Location')


class GitLabDeviceInstance(DeviceAdapter):
    default_branch = Field(str, 'Default Branch')
    visibility = Field(str, 'Visibility')
    ssh_url_to_repo = Field(str, 'SSH Repo Url')
    http_url_to_repo = Field(str, 'HTTP Repo Url')
    web_url = Field(str, 'Web Url')
    readme_url = Field(str, 'ReadMe Url')
    tag_list = ListField(str, 'Tag List')
    name_with_namespace = Field(str, 'Name With Namespace')
    path = Field(str, 'Path')
    path_with_namespace = Field(str, 'Path With Namespace')
    issues_enabled = Field(bool, 'Issues Enabled')
    open_issues_count = Field(int, 'Number Of Open Issues')
    merge_requests_enabled = Field(bool, 'Merge Requests Enabled')
    jobs_enabled = Field(bool, 'Jobs Enabled')
    wiki_enabled = Field(bool, 'Wiki Enabled')
    snippets_enabled = Field(bool, 'Snippet Enabled')
    can_create_merge_request_in = Field(bool, 'Can Create Merge Request')
    resolve_outdated_diff_discussions = Field(bool, 'Resolve Outdated Diff Discussions')
    container_registry_enabled = Field(bool, 'Container Registry Enabled')
    creator_id = Field(int, 'Creator ID')
    import_status = Field(str, 'Import Status')
    archived = Field(bool, 'Archived')
    avatar_url = Field(str, 'Avatar Url')
    shared_runners_enabled = Field(bool, 'Shared Runners Enabled')
    forks_count = Field(int, 'Forks Count')
    star_count = Field(int, 'Star Count')
    runners_token = Field(str, 'Runners Token')
    ci_default_git_depth = Field(int, 'CI Default Git Depth')
    public_jobs = Field(bool, 'Public Jobs')
    only_allow_merge_if_pipeline_succeeds = Field(bool, 'Only Allow Merge If Pipeline Succeeds')
    allow_merge_on_skipped_pipeline = Field(bool, 'Allow Merge On Skipped Pipelines')
    only_allow_merge_if_all_discussions_are_resolved = Field(bool, 'Only Allow Merge If All Discussions Are Resolved')
    remove_source_branch_after_merge = Field(bool, 'Remove Source Branch After Merge')
    request_access_enabled = Field(bool, 'Request Access Enabled')
    merge_method = Field(str, 'Merge Method')
    autoclose_referenced_issues = Field(bool, 'Autoclose Referenced Issues')
    suggestion_commit_message = Field(str, 'Suggestion Commit Message')
    marked_for_deletion_on = Field(datetime, 'Marked For Deletion On')
    shared_with_groups = ListField(Group, 'Shared With Groups')
    statistics = Field(Statistics, 'Statistics')
    namespace = Field(Namespace, 'Namespace')
    approvals_before_merge = Field(int, 'Approvals Before Merge')
    auto_cancel_pending_pipelines = Field(str, 'Auto Cancel Pending Pipelines')
    auto_devops_deploy_strategy = Field(str, 'Auto Devops Deploy Strategy')
    auto_devops_enabled = Field(bool, 'Auto Devops Enabled')
    build_coverage_regex = Field(str, 'Build Coverage Regex')
    build_timeout = Field(int, 'Build Timeout')
    builds_access_level = Field(str, 'Builds Access Level')
    ci_config_path = Field(str, 'CI Config Path')
    empty_repo = Field(bool, 'Empty Repo')
    external_authorization_classification_label = Field(str, 'External Authorization Classification Label')
    forking_access_level = Field(str, 'Forking Access Level')
    service_desk_address = Field(str, 'Service Desk Address')
    service_desk_enabled = Field(bool, 'Service Desk Enabled')
    vulnerability_findings = ListField(VulnerabilityFinding, 'Vulnerability Findings')


class GitLabUserInstance(UserAdapter):
    web_url = Field(str, 'Web URL')
    location = Field(str, 'Location')
    skype = Field(str, 'Skype')
    linkedin = Field(str, 'Linkedin')
    twitter = Field(str, 'Twitter')
    note = Field(str, 'Note')
    is_private = Field(bool, 'Private')
    current_ip = Field(str, 'Current Sign In IP', converter=format_ip, json_format=JsonStringFormat.ip)
    current_ip_raw = Field(str,
                           description='Number representation of the Public IP, useful for filtering by range',
                           converter=format_ip_raw,
                           hidden=True)
    last_ip = Field(str, 'Last Sign In IP', converter=format_ip, json_format=JsonStringFormat.ip)
    last_ip_raw = Field(str,
                        description='Number representation of the Public IP, useful for filtering by range',
                        converter=format_ip_raw,
                        hidden=True)
    projects = ListField(Project, 'Projects')
    user_groups = ListField(Group, 'User Groups')
