DEFAULT_TANIUM_PORT = '443'
GET_DEVICES_BODY_PARAMS = '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" ' \
                          'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:' \
                          'xsi="http://www.w3.org/2001/XMLSchema-instance">' \
                          '<SOAP-ENV:Body><typens:tanium_soap_request xmlns:typens="urn:TaniumSOAP">' \
                          '<command>GetObject</command><object_list><client_status/></object_list>' \
                          '<options><suppress_object_list>1</suppress_object_list></options>' \
                          '</typens:tanium_soap_request></SOAP-ENV:Body></SOAP-ENV:Envelope>'
