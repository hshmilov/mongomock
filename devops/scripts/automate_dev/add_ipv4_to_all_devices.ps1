# Run on the DC
$computers = Get-ADComputer -filter 'Name -like "DESKTOP-*"' | Select-Object -Property Name
$i = 0
foreach ($computer in $computers) {
    $i++
    if ($i -eq 254) { $i = 1}

    $ip = "192.168.30." + $i
    $computer = $computer.name
    Add-DnsServerResourceRecordA -Name $computer -ZoneName "TestSecDomain.test" -AllowUpdateAny -IPv4Address $ip -TimeToLive 01:00:00
    Write-Output "$computer -> $ip" | out-host
} #end foreach