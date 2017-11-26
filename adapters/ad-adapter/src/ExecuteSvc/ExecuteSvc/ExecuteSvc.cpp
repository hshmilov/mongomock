#include "ExecuteSvc.h"
#include <fstream>
#include <string>
#include <sstream>
#include <vector>
#include <stdio.h>

#define DEFAULT_INSTRUCTION_PATH "%windir%\\axon_instructions.cfg"
#define TEMP_RESULT_PATH "%windir%\\axoniusCommandResultTemp.txt"
#define RESULT_PATH "%windir%\\axoniusCommandResult.txt"
#define DEFAULT_COMMAND_SEPARATOR "_SEPARATOR_STRING_"

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
		TCHAR fullTempPath[MAX_PATH];
		TCHAR fullResultPath[MAX_PATH];

		// Exapnding environment string
		OutputDebugString("AXON: Expanding");
		DWORD requiredSizeTemp = ExpandEnvironmentStrings(TEMP_RESULT_PATH, fullTempPath, MAX_PATH);
		DWORD requiredSize = ExpandEnvironmentStrings(RESULT_PATH, fullResultPath, MAX_PATH);
		if (requiredSize >= MAX_PATH || requiredSizeTemp >= MAX_PATH)
		{
			// TODO: Think about what i should do here!
			OutputDebugString("AXON: Failed expanding environment variables");
		}

		// Trying to remove old result files (best effort)
		remove(fullTempPath);
		remove(fullResultPath);

		size_t pos = 0;
		std::string single_command;
		std::string separator(DEFAULT_COMMAND_SEPARATOR);

		// Splitting the cmd to single commands using predefined seperator
		while ((pos = data.find(separator)) != std::string::npos)
		{
			single_command = data.substr(0, pos);
			data.erase(0, pos + separator.length());
			// Try running the command
			std::string commandToRun = "/C " + single_command + " >> " + TEMP_RESULT_PATH;
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
			DWORD result = WaitForSingleObject(ShExecInfo.hProcess, 30 * 1000); // Wait for 30 seconds

			if (result != WAIT_OBJECT_0 || shellResult == FALSE)
			{
				OutputDebugString("AXON: Executing command failed");
			}

			OutputDebugString("AXON: Writing separator back to temp file");
			std::ofstream resultFile(fullTempPath, std::ofstream::app);
			if (resultFile.is_open())
			{
				resultFile << DEFAULT_COMMAND_SEPARATOR;
			}
			else
			{
				OutputDebugString("AXON: Cant open temp result file");
			}
			resultFile.close();
		}

		// Renaming the temp file
		if (0 != rename(fullTempPath, fullResultPath))
		{
			OutputDebugString("AXON: Rename file failed!");
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