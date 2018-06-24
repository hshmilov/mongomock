"""
The best mocking we can have for an adapter we don't have.
"""
import random
import time
from flask import Flask, jsonify, request

app = Flask(__name__)

# Credentials for admin
GOOD_USER_USERNAME = "admin"
GOOD_USER_PASSWORD = "admin"
TOKEN = "123456789"

# Credentials for maximum login limit
BAD_USER_USERNAME = "too"
BAD_USER_PASSWORD = "much"

GOOD_REQUEST_CHANCES = 0.9


def build_sc_response(data, error=None):
    """
    Gets a reponse object and returns the whole response to be returned.
    :param data:
    :return:
    """

    final_object = {}

    if error is not None:
        final_object["type"] = "error"
        final_object["error_code"] = 123
        final_object["error_msg"] = error
        final_object["warnings"] = ["warning 1"]
        final_object["timestamp"] = int(time.time())

    else:
        final_object["type"] = "regular"
        final_object["error_code"] = 0
        final_object["error_msg"] = ""
        final_object["warnings"] = []
        final_object["timestamp"] = int(time.time())
        final_object['response'] = data

    return jsonify(final_object)


@app.route("/rest/token", methods=['POST', 'DELETE'])
def token():
    if request.method == "DELETE":
        return build_sc_response({})

    json_params = request.get_json()
    username = json_params['username']
    password = json_params['password']

    # according to the api:
    # NOTE #3: On response if releaseSession returns "true", the user has reached its maximum login limit.

    if username == GOOD_USER_USERNAME and password == GOOD_USER_PASSWORD:
        regular_token = True
    elif username == BAD_USER_USERNAME and password == BAD_USER_PASSWORD:
        regular_token = False
    else:
        # bad username and password
        build_sc_response({}, error="Invalid Username and Password")

    if regular_token is False:
        return build_sc_response({"releaseSession": True})
    else:
        return build_sc_response({"token": TOKEN})


@app.route("/rest/system")
def system():
    # The whole resonse is not here (see https://docs.tenable.com/sccv/api/System.html)
    return build_sc_response({"version": "5.0.0"})


@app.route("/rest/ipInfo")
def ip_info():
    token = request.headers.get("X-SecurityCenter")
    print(f"Token is {token}")
    if token != TOKEN:
        return build_sc_response({}, error="Invalid Token")

    # Randomly drop the request to check if the adapter takes it
    if random.random() > GOOD_REQUEST_CHANCES:
        return build_sc_response({}, error="Randomly dropping")

    ip = request.args.get("ip")
    fields = request.args.get("fields", [])

    assert ip is not None

    if type(fields) == str:
        fields = fields.split(",")

    ip_to_list = [int(x) for x in ip.split(".")]
    repository_id = str(ip_to_list[0])
    mac = "00:00:%0.2x:%0.2x:%0.2x:%0.2x" % (ip_to_list[0], ip_to_list[1], ip_to_list[2], ip_to_list[3])
    security_critical_number = random.randint(1, 100)

    response = {
        "repositories": [
            {
                "id": repository_id,
                "name": f"Rep {repository_id}",
                "description": ""
            }
        ],
        "ip": ip,
        "repositoryID": repository_id,
        "score": "2130",
        "total": str(310 + security_critical_number),
        "severityInfo": "110",
        "severityLow": "7",
        "severityMedium": "41",
        "severityHigh": "152",
        "severityCritical": str(security_critical_number),
        "macAddress": mac,
        "policyName": f"Security Policy {ip_to_list[1]}",
        "pluginSet": "",
        "netbiosName": f"TARGET\\{ip}",
        "dnsName": f"{ip}.target.domain.com",
        "osCPE": "cpe:\/o:microsoft:windows_7::gold:x64-ultimate",
        "biosGUID": "",
        "tpmID": "",
        "mcafeeGUID": "",
        "lastAuthRun": str(int(time.time())),
        "lastUnauthRun": "",
        "severityAll": f"{security_critical_number},152,41,7,110",
        "os": "Microsoft Windows 7 Ultimate",
        "hasPassive": random.choice(["No", "Yes"]),
        "hasCompliance": random.choice(["No", "Yes"]),
        "lastScan": str(int(time.time())),
        "links": [
            {
                "name": "SANS",
                "link": f"https:\/\/isc.sans.edu\/ipinfo.html?ip={ip}"
            },
            {
                "name": "ARIN",
                "link": f"http:\/\/whois.arin.net\/rest\/ip\/{ip}"
            }
        ],
        "repository": {
            "id": repository_id,
            "name": f"Rep {repository_id}",
            "description": ""
        }
    }

    # there are fields that must be there
    fields.extend(['ip', 'repositoryID'])

    # remove unneeded fields to mock only wanted fields
    final_response = {}
    for field in fields:
        final_response[field] = response[field]

    return build_sc_response(response)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port="33332")
