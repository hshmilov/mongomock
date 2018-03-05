/*
This service should run using the psexec alternative by impacket.
This service will run an exe defined by the 'DEFAULT_EXE_PATH'

Author: Ofir Yefet
*/

#pragma once

#include <Windows.h>

extern HANDLE hStopServiceEvent;

void _ServiceMain(void*);
void DeleteSvc();