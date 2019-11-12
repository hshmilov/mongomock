import copy
import ssl

from flask import Flask, json, request

FLASK_APP = Flask(__name__)

BAD_APP_ID = ({'ErrorCode': 'APPAP008E',
               'ErrorMsg': 'Problem occurred while trying to use user in the Vault '
                           '(Error: ITATS982E User {app_id} is not defined.  Diagnostic Info: 6)'},
              403)

BAD_QUERY = ({'ErrorCode': 'APPAP004E',
              'ErrorMsg': 'Password object matching query [{query}] was not found (Diagnostic Info: 9). '
                          'Please check that there is a password object that answers your query in the Vault '
                          'and that both the Provider and the application user have the appropriate permissions '
                          'needed in order to use the password.'},
             404)

SUCCESS_RESPONSE = {'Content': 'Password2', 'PolicyID': 'WinDesktopLocal', 'Name': 'windows1', 'SequenceID': '5',
                    'UserName': 'svc_account', 'CPMStatus': 'success', 'Folder': 'Root\\OS\\Windows', 'Safe': 'Test',
                    'Address': 'components', 'LastSuccessVerification': '1563922115', 'LogonDomain': 'components',
                    'DeviceType': 'Operating System', 'LastTask': 'VerifyTask', 'RetriesCount': '-1',
                    'LastSuccessChange': '1563908108', 'CreationMethod': 'PVWA', 'PasswordChangeInProcess': 'False'}
GOOD_QUERY = r'Safe=Test;Folder=root\OS\Windows;Object=windows1'


@FLASK_APP.route('/AIMWebService/api/Accounts/')
def actual():
    appid = request.args.get('AppID')
    query = request.args.get('Query')
    if appid != 'testappid':
        error_response = copy.deepcopy(BAD_APP_ID)
        error_response[0]['ErrorMsg'].format(query=query)
        return json.dumps(error_response[0]), error_response[1]

    if query != GOOD_QUERY:
        error_response = copy.deepcopy(BAD_QUERY)
        error_response[0]['ErrorMsg'].format(app_id=appid)
        return json.dumps(error_response[0]), error_response[1]

    return json.dumps(SUCCESS_RESPONSE)


@FLASK_APP.route('/')
def main():
    return 'Found'


if __name__ == '__main__':
    CONTEXT = ssl.SSLContext()
    CONTEXT.load_cert_chain('/src/server.cert', '/src/server.key')
    FLASK_APP.run(host='0.0.0.0', port=5000, ssl_context=CONTEXT)
