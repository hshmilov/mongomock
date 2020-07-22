DEVICE_PAGINATION = 50

ASSET_QUERY = 'Select * from public.dim_asset'
VULNERABILITIES_QUERY = 'Select * from public.dim_vulnerability '
ASSET_VULNERABILITIES_QUERY = 'Select * from public.fact_asset_vulnerability_instance'
INSTALLED_SOFTWARE_QUERY = 'Select * from public.dim_asset_software'
SERVICES_QUERY = 'Select * from public.dim_asset_service'
USERS_QUERY = 'Select * from public.dim_asset_user_account'
GROUPS_QUERY = 'Select * from public.dim_asset_group_account'
ASSET_TAGS_QUERY = 'Select * from public.dim_asset_tag'
TAGS_QUERY = 'Select * from public.dim_tag'
POLICIES_QUERY = 'Select * from public.dim_policy'
ASSET_POLICIES_QUERY = 'Select * from public.fact_asset_policy'
