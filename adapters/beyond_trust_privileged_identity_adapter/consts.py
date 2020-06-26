from enum import Enum


API_PREFIX = 'ERPMWebService/AuthService.svc/REST'

DOMAIN_ACCOUNTS = {
    0: 'Manager Type Explicit User',
    1: 'Manager Type Domain User',
    2: 'Manager Type Domain Group',
    3: 'Manager Type Self Recovery',
    4: 'Manager Type Role',
    5: 'Manager Type Radius',
    6: 'Manager Type Certificate',
    7: 'Manager Type LDAP User'
}


class AuthenticationMethods(Enum):
    NativeStaticAccount = 'Native Static Account'
    FullyQualifiedAccount = 'Fully Qualified Account'
    IntegratedAuthentication = 'Integrated Authentication'
    CertificateAuthentication = 'Certificate Authentication'


AUTHENTICATION_METHOD_CONVERT = {
    AuthenticationMethods.NativeStaticAccount.value: 1,
    AuthenticationMethods.FullyQualifiedAccount.value: 2,
    AuthenticationMethods.IntegratedAuthentication.value: 3,
    AuthenticationMethods.CertificateAuthentication.value: 4,

}
