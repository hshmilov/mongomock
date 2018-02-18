# Eset Connection!

The File `eset_conncetion.cpp` wraps the ServerApi.so
for communicating with Eset Remote Administrator.

It publishes 3 functions:
* int Init() - Initiates all the handles of functions that communicates with the server as well as Guard classes for cleanup.
* const char* SendMessage(const char* request) - Sends messages and returns responses from the ERA server.
* void FreeResponse(char* szRes) - Cleans up messages (pointers) returned from the server. 

Sadly eset didn't release any linux compatible examples and this was based off something from the forum:
https://forum.eset.com/topic/11213-eset-cli-c-api-for-linux/

The shared libraries:
* Network.so
* Protobuf.so
* ServerApi.so

Can be found on the installed
ERA server in the correct version `/opt/eset/RemoteAdministrator/Server`.
