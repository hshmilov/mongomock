SKIP_DEPLOYMENT_MARKER = 'deploy_skip.marker'

FILENAMES_EXCLUDE_GLOBAL = ['.git',
                            '.idea',
                            '.cache',
                            '__pycache__',
                            'tests',
                            'adapters/debug_main.py',
                            'plugins/debug_main.py',
                            'deployment/make.py',
                            'deployment/run_tests.py',
                            'deployment/run_tests.sh']

DIRS_EXCLUDE_GLOBAL = ['venv',
                       'logs',
                       'devops/systemization',
                       'devops/CI',
                       'deploy_artifacts',
                       'plugins/gui/frontend/node_modules',
                       'plugins/gui/frontend/dist',
                       'testing/test_credentials']

CURRENT_STATE_FILE_VERSION = 1.1
