USER = 'username'
PASSWORD = 'password'
MICROSOFT_KMS_HOST = 'server'
MICROSOFT_KMS_PORT = 'port'
DEFAULT_MICROSOFT_KMS_PORT = 1433
MICROSOFT_KMS_DATABASE = 'database'
DEVICES_FETECHED_AT_A_TIME = 'devices_fetched_at_a_time'
MICROSOFT_KMS_QUERY = 'SELECT [FullyQualifiedDomainName],[ProductName],[ProductDescription],[ProductVersion],' \
                      '[LicenseFamily],[ApplicationId],[InstallationId],[ConfirmationId],[SoftwareProvider],' \
                      '[ProductKeyId],[ProductKeyType],[PartialProductKey],[Sku],[LicenseStatus],' \
                      '[LicenseStatusReason],[GraceExpirationDate],[ActionsAllowed],[GenuineStatus],' \
                      '[LicenseStatusLastUpdated],[CMID],[KmsHost],[KmsPort],[VLActivationType],' \
                      '[VLActivationTypeEnabled],[AdActivationObjectName],[AdActivationObjectDN],' \
                      '[AdActivationCsvlkPid],[AdActivationCsvlkSkuId],[LastActionStatus],' \
                      '[LastErrorCode],[LastUpdated],[ExportGuid],[RowVer] FROM [ADK].[base].[ActiveProduct]'
