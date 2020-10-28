COMPLIANCE_AWS_RULES_COLLECTION = 'aws_rules'
COMPLIANCE_AZURE_RULES_COLLECTION = 'azure_rules'

# List of all compliance modules, by adapter_name
# If a module does not match an adapter name, add specific logic to compliance.py: `get_initial_cis_selection`
COMPLIANCE_MODULES = [
    'aws',
    'azure',
    'oracle_cloud'
]

COMPLIANCE_RULES_COLLECTIONS = {
    module: f'{module}_rules'
    for module in COMPLIANCE_MODULES
}


COMPLIANCE_REPORTS_COLLECTIONS = {
    module: f'{module}_reports' for module in COMPLIANCE_MODULES
}
COMPLIANCE_REPORTS_COLLECTIONS['aws'] = 'reports'  # Special exception for the case of aws


# Stuff for report generation
NUMBER_OF_PARALLEL_PROCESSES = 5
TIMEOUT_FOR_RESULT_GENERATION = 60 * 60 * 5  # 5 hours
