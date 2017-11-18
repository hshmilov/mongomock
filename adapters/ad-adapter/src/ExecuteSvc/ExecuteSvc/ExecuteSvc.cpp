#include "ExecuteSvc.h"
#include <fstream>
#include <string>
#include <sstream>
#include <vector>

#define DEFAULT_INSTRUCTION_PATH "%windir%\\axon_instructions.cfg"

void performAction(std::string line)
{
	std::istringstream line_stream(line);
	std::string param;
	std::vector<std::string> parameters;
	while (std::getline(line_stream, param, ';'))
	{
		parameters.push_back(param);
	}
	if (parameters.size() != 2)
	{
		// We only support command;data format, any other format is not supported
		return; // TODO: Think about a way to send return value to the issuer
	}

	std::string commandType = parameters[0];
	std::string data = parameters[1];

	if ("exe" == commandType)
	{
		// Should run exe file from the given address

		// Exepnding env string
		TCHAR fullExePath[MAX_PATH];
		DWORD requiredSize = ExpandEnvironmentStrings(data.c_str(), fullExePath, MAX_PATH);
		if (requiredSize < MAX_PATH)
		{
			STARTUPINFO si;
			PROCESS_INFORMATION pi;
			ZeroMemory(&si, sizeof(si));
			si.cb = sizeof(si);
			ZeroMemory(&pi, sizeof(pi));

			// Running the wanted exe
			OutputDebugString("AXON: Starting default process");
			CreateProcess(fullExePath, NULL, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi);
			OutputDebugString("AXON: Process created, waiting");
			while (WaitForSingleObject(hStopServiceEvent, 10) != WAIT_OBJECT_0)
			{
			}
		}

	}
	else if ("cmd" == commandType)
	{
		// Should run a cmd
		std::string commandToRun = "/C " + data + " > %windir%\\axoniusCommandResult.txt";
		OutputDebugString((std::string("AXON: Command to run is ") + commandToRun).c_str());

		SHELLEXECUTEINFO ShExecInfo = { 0 };
		ShExecInfo.cbSize = sizeof(SHELLEXECUTEINFO);
		ShExecInfo.fMask = SEE_MASK_NOCLOSEPROCESS;
		ShExecInfo.hwnd = NULL;
		ShExecInfo.lpVerb = NULL;
		ShExecInfo.lpFile = "cmd.exe";
		ShExecInfo.lpParameters = commandToRun.c_str();
		ShExecInfo.lpDirectory = NULL;
		ShExecInfo.nShow = SW_SHOW;
		ShExecInfo.hInstApp = NULL;
		BOOL shellResult = ShellExecuteEx(&ShExecInfo);
		DWORD result = WaitForSingleObject(ShExecInfo.hProcess, 30*1000); // Wait for 30 seconds

		if (result != WAIT_OBJECT_0 || shellResult == FALSE)
		{
			OutputDebugString("AXON: Executing command failed");
		}

	}
}

void _ServiceMain(void*)
{
	OutputDebugString("AXON: Starting process");
	TCHAR fullPath[MAX_PATH];

	// Exapnding environment string
	OutputDebugString("AXON: Expanding");
	DWORD requiredSize = ExpandEnvironmentStrings(DEFAULT_INSTRUCTION_PATH, fullPath, MAX_PATH);
	if (requiredSize < MAX_PATH)
	{
		OutputDebugString("AXON: getting result");
		std::ifstream confFile(fullPath);
		std::string line;

		while (std::getline(confFile, line))
		{
			OutputDebugString("AXON: Performing action");
			performAction(line);
		}
	}
	else
	{
		OutputDebugString("AXON: Failed expanding environment variables");
	}

	OutputDebugString("AXON: Deleting service");

	DeleteSvc();

	CloseHandle(hStopServiceEvent);
}