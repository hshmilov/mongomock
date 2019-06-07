GET_DEVICES_BODY_PARAMS = '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" ' \
                          'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:' \
                          'xsi="http://www.w3.org/2001/XMLSchema-instance">' \
                          '<SOAP-ENV:Body><typens:tanium_soap_request xmlns:typens="urn:TaniumSOAP">' \
                          '<command>GetObject</command><object_list><client_status/></object_list>' \
                          '<options><suppress_object_list>1</suppress_object_list></options>' \
                          '</typens:tanium_soap_request></SOAP-ENV:Body></SOAP-ENV:Envelope>'

GET_DEVICES_BODY_PARAMS_PAGINTAED = '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" ' \
                                    'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:' \
                                    'xsi="http://www.w3.org/2001/XMLSchema-instance">' \
                                    '<SOAP-ENV:Body><typens:tanium_soap_request xmlns:typens="urn:TaniumSOAP">' \
                                    '<command>GetObject</command><object_list><client_status/></object_list>' \
                                    '<options><row_start>{0}</row_start><row_count>{1}</row_count>' \
                                    '<cache_expiration>{2}</cache_expiration>' \
                                    '<cache_sort_fields>last_registration</cache_sort_fields>' \
                                    '</options>' \
                                    '</typens:tanium_soap_request></SOAP-ENV:Body></SOAP-ENV:Envelope>'
DEVICE_PER_PAGE = 50
CACHE_EXPIRATION = 600
