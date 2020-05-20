DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000
# Note! After this time the process will be terminated. We shouldn't ever
# terminate a process while it runs, in case its the execution we might leave
# some files on the target machine which is a bad idea. For exactly this reason
# we have another mechanism to reject execution promises on the
# execution-requester side. This value should be for times we are really really
# sure there is a problem.
MAX_SUBPROCESS_TIMEOUT = 60 * 60
WMI_NAMESPACE = '//./root/cimv2'
