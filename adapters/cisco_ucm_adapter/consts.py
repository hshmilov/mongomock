AXL_POST_BODY = '<soapenv:Envelope ' \
                'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" ' \
                'xmlns:ns="http://www.cisco.com/AXL/API/12.5">' \
                '<soapenv:Header /><soapenv:Body>' \
                '<ns:listPhone>' \
                '<searchCriteria>' \
                '<name>%</name>' \
                '</searchCriteria>' \
                '<returnedTags>' \
                '<name></name>' \
                '</returnedTags>' \
                '</ns:listPhone>' \
                '</soapenv:Body></soapenv:Envelope>'
