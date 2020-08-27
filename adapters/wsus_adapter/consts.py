PASSWORD = 'password'
USER = 'username'
WSUS_HOST = 'host'
WMI_WORKING_DIR = 'cwd'
WMI_WORKING_DIR_DEFAULT = 'C:\\windows\\temp'
WMI_OUTPUT_FILE = 'output_file'

PS_SUBCOMMAND_PREPARE_COMPUTER_SCOPE = (
    '[void][reflection.assembly]::LoadWithPartialName(\'Microsoft.UpdateServices.Administration\'); '
    '$ComputerScope = New-Object Microsoft.UpdateServices.Administration.ComputerTargetScope; '
    '$ComputerScope.IncludeDownstreamComputerTargets = $true'
)
PS_COMMAND_TARGETS = '(Get-WsusServer).GetComputerTargets($ComputerScope)'
PS_COMMAND_TARGET_COUNT = (f'{PS_SUBCOMMAND_PREPARE_COMPUTER_SCOPE}; '
                           '(Get-WsusServer).GetComputerTargetCount($ComputerScope)')
