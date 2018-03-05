#pragma once

#include <windows.h>
#include <tchar.h>
#include <stdio.h>
#include <stdlib.h>
#include <winsvc.h>
#include <process.h>

SERVICE_STATUS          ServiceStatus;
SERVICE_STATUS_HANDLE   ServiceStatusHandle;

#define SERVICENAME _T("ExecuteSvc")
HANDLE hStopServiceEvent;


int _tmain(int, LPTSTR*);

void DeleteSvc();

VOID WINAPI ExecuterStart(DWORD, LPTSTR*);

VOID WINAPI ExecuterCtrlHandler(DWORD Opcode);

DWORD IsService(BOOL& isService);