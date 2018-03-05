#include <windows.h>
#include <fstream>

/* This is an example for some exe we can run using the service executer
*/

int main()
{
	std::fstream fs;
	fs.open("c:\\temp\\payloadResult.txt", std::fstream::in | std::fstream::out | std::fstream::app);
	fs << "Success!!! Avigdor!!!";

	fs.close();

	return 0;
}