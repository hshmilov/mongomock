#include <string>
#include <cstring>
#include <errno.h>
#include <dlfcn.h>
#include <iostream>

typedef int (*era_process_request)(const char* request, char** response);
typedef void (*era_free)(char* s);
typedef int (*era_init_lib)();
typedef void (*era_deinit_lib)();

class LibCloseGuard{
    public:
        void *hmod;

        ~LibCloseGuard(){
            if (hmod){
                ::dlclose(hmod);
            }
        };
};

class LibDeInitGuard{
    public:
        era_deinit_lib deinit;
        ~LibDeInitGuard(){
            if (deinit){
                deinit();
            }
        };
};

LibCloseGuard close_guard;
LibDeInitGuard deinit_guard;
era_process_request send_request = NULL;
era_free free_response = NULL;
const char* state = "Started";

__attribute__((constructor)) void dll_init(void)
{
    void* handle = ::dlopen( "/home/axonius/bin/ServerApi.so", RTLD_LAZY | RTLD_GLOBAL );

    // Load library
    if (!handle)
    {
        state = "Cannot load api library error.";
        return;
    }

    close_guard.hmod = handle;

    // Get pointer to function, which can initialize library
    era_init_lib init_lib = (era_init_lib)::dlsym(close_guard.hmod, "era_init_lib");
    if (!init_lib )
    {
        state = "Cannot init library";
        return;
    }

    // Get pointer to function, which can deinitialize library
    era_deinit_lib deinit_lib = (era_deinit_lib)::dlsym(handle, "era_deinit_lib");
    if (!deinit_lib)
    {
        state = "Cannot deinit libraries";
        return;
    }

    // Initialize library
    int res = init_lib();
    if(res)
    {
        state = "Init lib result: " + res;
        return;
    }

    deinit_guard.deinit = deinit_lib;

    send_request = (era_process_request)::dlsym(handle, "era_process_request");
    if (!send_request)
    {
        state = "Cannot load era_process_request";
        return;
    }

    // Get pointer to function, which can free response
    free_response = (era_free)::dlsym(close_guard.hmod, "era_free");
    if (!free_response)
    {
        state = "Cannot load era_free";
        return;
    }

    state = "Ready";
}

extern "C" const char* SendMessage(const char* request)
{
    int result = -1;
    char* response = NULL;

    // Send request and receive response + free response
    result = send_request(request,&response);

    return response;
}

extern "C" const char* GetState()
{
    return state;
}

extern "C" void FreeResponse(char* Res)
{
    free_response(Res);
}