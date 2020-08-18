DEVICE_PAGINATION = 50

ASSET_QUERY = 'Select asset_id,mac_address,host_name,host_type,ip_address,os_vendor,os_family,os_version,' \
              'os_architecture,os_type,os_name,os_description,os_system,os_cpe,credential_status,risk_modifier,' \
              'last_assessed_for_vulnerabilities,sites from public.dim_asset'
VULNERABILITIES_QUERY = 'Select vulnerability_id,nexpose_id,title,date_published,date_added,date_modified,' \
                        'severity_score,severity,critical,severe,moderate,pci_severity_score,pci_status,' \
                        'pci_failures,risk_score,cvss_vector,cvss_score,pci_adjusted_cvss_score,' \
                        'denial_of_service,exploits,' \
                        'malware_kits,malware_popularity,cvss_v3_vector,cvss_v3_score from public.dim_vulnerability '
ASSET_VULNERABILITIES_QUERY = 'Select asset_id, vulnerability_id from public.fact_asset_vulnerability_instance'
INSTALLED_SOFTWARE_QUERY = 'Select asset_id,vendor,name,version from public.dim_asset_software'
SERVICES_QUERY = 'Select asset_id,service,port,protocol,vendor,family,name,version,certainty,credential_status ' \
                 'from public.dim_asset_service'
USERS_QUERY = 'Select asset_id,name,full_name from public.dim_asset_user_account'
GROUPS_QUERY = 'Select asset_id,name from public.dim_asset_group_account'
ASSET_TAGS_QUERY = 'Select asset_id,tag_id from public.dim_asset_tag'
TAGS_QUERY = 'Select tag_id,name,type,source,created,risk_modifier,color from public.dim_tag'
POLICIES_QUERY = 'Select policy_id,benchmark_id,policy_name,policy_version,title,description,' \
                 'unscored_rules from public.dim_policy'
ASSET_POLICIES_QUERY = 'Select asset_id,policy_id from public.fact_asset_policy'
