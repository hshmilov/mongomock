CLIENT_DETAILS = {}

# pylint: disable=line-too-long

# Axonius Trial Account, expired in Apr. 11 '20,
# So no API more access anymore, If you want to test data for SumoLogic, do the following:
# 1. Login into SumoLogic, run the query of your choice to test your feature
# 2. Export the results into a csv, put it inside the SumoLogicAdapter directory ,
#       lets assume named "search-results-2020-06-04T03_07_30.135-0700.csv"
#    Note: You might need to remove '_raw' column wholy as its json encoding is not readable by python
# 2. shove a `return` in the beginning of `sumo_logic_adapter.connection.SumoLogicConnection._connect`
# 3. shove the following code into the beginning of `sumo_logic_adapter.connection.SumoLogicConnection.iter_search_results`
##        from axonius.utils.parsing import make_dict_from_csv
##        from pathlib import Path
# yield from make_dict_from_csv((Path(__file__).parent / 'search-results-2020-06-04T03_07_30.135-0700.csv').read_text('utf-8'))
# return
# 4. run the adapter with whatever client_config, it will be green and the results would be consumed from your csv :)

# Device data credentials
#    'domain': 'https://service.us2.sumologic.com/',
#    'access_id': 'sut1Afpg2s48Fe',
#    'access_key': 'U4qh8te9swfdOG4XqAOh72bcjhjX5budEzmpZMbPZkBSrRMiaIiorTn515TxrqdL',
#    'is_users': False,
#    'search_query': '| _sourceHost as hostname'
#                    '| limit 1',
#    'verify_ssl': False, }

# User data credentials
# 'domain': 'https://service.us2.sumologic.com/',
# 'access_id': 'sut1Afpg2s48Fe',
# 'access_key': 'U4qh8te9swfdOG4XqAOh72bcjhjX5budEzmpZMbPZkBSrRMiaIiorTn515TxrqdL',
# 'is_users': True,
# 'search_query': '| "test" as id'
#                 '| "test" as domain'
#                 '| "test" as firstname'
#                 '| "test" as lastname'
#                 '| "test" as mail'
#                 '| "test" as assetname'
#                 '| "test" as username'
#                 '| limit 1',
# 'verify_ssl': False, }


SOME_DEVICE_ID = ''  # 'sut1Afpg2s48Fe_fCBfc291cmNlSG9zdCBhcyBob3N0bmFtZXwgbGltaXQgMQ=='
