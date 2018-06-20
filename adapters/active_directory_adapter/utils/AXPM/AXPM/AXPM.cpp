#include "stdafx.h"
#include <Wuapi.h>
#include <atlbase.h>
#include <iostream>
#include <string>
#include <stdio.h>
#include <comdef.h>
#include <ATLComTime.h>
#include <comutil.h>
#include <string.h>
#include "nlohmann/json.hpp"	// downloaded json package https://github.com/nlohmann/json

#define LCID_EN_US (0x409)


// for convenience
using json = nlohmann::json;

void print_to_stderr(const char * error_message, HRESULT error_code)
{
	_com_error err(error_code);
	LPCTSTR error_code_as_string = err.ErrorMessage();
	fprintf(stderr, "%s: %ws (%#lx)\n", error_message, error_code_as_string, error_code);
}

void print_usage(const char * const app_name)
{
	fprintf(stderr, "Usage: %s [path_to_wsusscn2.cab] [0/1]\n", app_name);
}

char * bstr_to_string(BSTR s)
{
	if (SysStringLen(s) == 0)
	{
		return (char *)"";
	}
	else
	{
		return _com_util::ConvertBSTRToString(s);
	}
}

int get_update(CComPtr<IUpdate> update, json * update_list)
{
	/* Prints to the screen details of an update (i.e. a patch that is needed to be installed).
	The function gets a point to a COM object of type IUpdate and prints useful information we use.
	*/
	HRESULT rc = NULL;
	CComPtr<ICategoryCollection> category_collection = NULL;
	CComPtr<IStringCollection> kb_article_ids_collection = NULL;
	CComPtr<IStringCollection> security_bulletin_ids_collection = NULL;
	CComPtr<ICategory> category = NULL;
	long category_count = 0;
	long kb_article_ids_count = 0;
	long security_bulletin_ids_count = 0;
	UpdateType update_type = utSoftware;
	BSTR category_name = NULL;
	BSTR str = NULL;	// generic var for IStringCollection
	BSTR title = NULL;
	BSTR msrc_severity = NULL;
	DATE depdate = NULL;
	json final_update = {};

	// Get all sort of details about the update. For a full list of details,
	// see https://msdn.microsoft.com/en-us/library/windows/desktop/aa386099(v=vs.85).aspx
	rc = update->get_Title(&title);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call IUpdate::get_Title", rc);
		return -1;
	}
	final_update["Title"] = bstr_to_string(title);

	// Get MSRC Severity (e.g., Critical)
	rc = update->get_MsrcSeverity(&msrc_severity);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call IUpdate::get_MsrcSeverity", rc);
		return -1;
	}
	final_update["MsrcSeverity"] = bstr_to_string(msrc_severity);

	// Get Date
	// Notice that LastDeploymentChangeTime is the time when this was changed on the remote server.
	// If we are using online microsoft wsus or wsusscn2.cab, this will be the correct time. But if we are using a custom wsus server (dc role)
	// Then this could be the time of deployment on this server.
	rc = update->get_LastDeploymentChangeTime(&depdate);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call IUpdate::get_LastDeploymentChangeTime", rc);
		return -1;
	}

	// This is a transformation we have to do from depdate to seconds since epoch.
	final_update["LastDeploymentChangeTime"] = (double)depdate * 86400 - 2209161600;

	// Get type. This could be 'Software' or 'Driver'.
	rc = update->get_Type(&update_type);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call IUpdate::get_Type", rc);
		return -1;
	}
	if (update_type == utDriver) {
		final_update["Type"] = "Driver";
	}
	else if (update_type == utSoftware) {
		final_update["Type"] = "Software";
	}
	else {
		final_update["Type"] = "Unknown";
	}

	// Get categories. This is a list of categories, e.g. "Windows 2008", "Visual Studio"
	rc = update->get_Categories(&category_collection.p);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call IUpdate::get_Categories", rc);
		return -1;
	}

	rc = category_collection->get_Count(&category_count);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call ICategoryCollection::get_Count", rc);
		return -1;
	}

	final_update["Categories"] = json::array();

	for (int i = 0; i < category_count; i++)
	{
		rc = category_collection->get_Item(i, &category.p);
		if (FAILED(rc))
		{
			print_to_stderr("Failed to call ICategoryCollection::get_Item", rc);
			return -1;
		}

		rc = category->get_Name(&category_name);
		if (FAILED(rc))
		{
			print_to_stderr("Failed to call ICategory::get_Name", rc);
			return -1;
		}
		final_update["Categories"].push_back(bstr_to_string(category_name));
	}

	// Get a list of KB's attached to this patch
	rc = update->get_KBArticleIDs(&kb_article_ids_collection.p);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call IUpdate::get_KBArticleIDs", rc);
		return -1;
	}

	rc = kb_article_ids_collection->get_Count(&kb_article_ids_count);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call IStringCollection::get_Count for KB Article ID's", rc);
		return -1;
	}

	final_update["KBArticleIDs"] = json::array();

	for (int i = 0; i < kb_article_ids_count; i++)
	{
		rc = kb_article_ids_collection->get_Item(i, &str);
		if (FAILED(rc))
		{
			print_to_stderr("Failed to call IStringCollection::get_Item for KB Article ID's", rc);
			return -1;
		}
		final_update["KBArticleIDs"].push_back(bstr_to_string(str));
	}

	// Get a list of Security Bulletin ID's attached to this patch
	rc = update->get_SecurityBulletinIDs(&security_bulletin_ids_collection.p);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call IUpdate::get_SecurityBulletinIDs", rc);
		return -1;
	}

	rc = security_bulletin_ids_collection->get_Count(&security_bulletin_ids_count);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call IStringCollection::get_Count for Security Bulletin ID's", rc);
		return -1;
	}

	final_update["SecurityBulletinIDs"] = json::array();

	for (int i = 0; i < security_bulletin_ids_count; i++)
	{
		rc = security_bulletin_ids_collection->get_Item(i, &str);
		if (FAILED(rc))
		{
			print_to_stderr("Failed to call IStringCollection::get_Item for Security Bulletin ID's", rc);
			return -1;
		}
		final_update["SecurityBulletinIDs"].push_back(bstr_to_string(str));
	}

	// append the final update to the update list
	update_list->push_back(final_update);

	return 0;
}
	
int _main(int argc, char *argv[])
{
	HRESULT rc = NULL;
	bool should_check_online = false;
	CComPtr<IUpdateServiceManager> service_manager = NULL;
	CComPtr<IUpdateService> update_service = NULL;
	BSTR update_service_manager_service_id = NULL;
	CComPtr<IUpdateSession2> session = NULL;
	CComPtr<IUpdateSearcher> searcher = NULL;
	CComPtr<ISearchResult> search_result = NULL;
	CComPtr<IUpdateCollection> updateCollection = NULL;
	CComPtr<IUpdate> update = NULL;
	OperationResultCode search_result_code = orcFailed;
	long updateCount = 0;
	json update_list = json::array();

	// Needed to convert ascii to OLE
	USES_CONVERSION;

	// Validate Arguments
	if (argc < 2 || argc > 3)
	{
		print_usage(argv[0]);
		return -1;
	}

	if (strcmp(argv[1], "0") == 0)
	{
		should_check_online = false;
		if (argc != 3)
		{
			// we have to have exactly 3 arguments in this case.
			print_usage(argv[0]);
			return -1;
		}
	}
	else if (strcmp(argv[1], "1") == 0)
	{
		should_check_online = true;
	}
	else
	{
		print_usage(argv[0]);
		return -1;
	}

	// Initialize COM. 
	rc = CoInitialize(NULL);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to initialize COM", rc);
		return -1;
	}

	if (should_check_online == false)
	{
		// Since we are not using the default internet service, we need to create an update service manager.
		// We create an IUpdateServiceManager, to be able to add an offline file for getting update results.
		rc = service_manager.CoCreateInstance(__uuidof(UpdateServiceManager));
		if (FAILED(rc))
		{
			print_to_stderr("Failed to create IUpdateServiceManager", rc);
			return -1;
		}

		// Now lets add the offline updates cab file that we downloaded from microsoft.
		rc = service_manager->AddScanPackageService(SysAllocString(L"Offline Sync Service"), SysAllocString(A2COLE(argv[2])), 0, &update_service.p);
		if (FAILED(rc))
		{
			print_to_stderr("Failed to add scan package service", rc);
			return -1;
		}

		// Finally, we need the service id of the service we just successfully created, since we will add it to the searcher soon.
		rc = update_service->get_ServiceID(&update_service_manager_service_id);
		if (FAILED(rc))
		{
			print_to_stderr("Failed to get the service id of the add scan package service", rc);
			return -1;
		}
	}

	// Now we can continue to the update search.
	// Get the com COM object called IUpdateSession. This is also called 'Microsoft.Update.Session' and it represents WUA - Windows Update Agent.
	rc = session.CoCreateInstance(__uuidof(UpdateSession));
	if (FAILED(rc))
	{
		print_to_stderr("Failed to create IUpdateSession", rc);
		return -1;
	}

	// Lets set up the locale to english, otherwise it would use the default UI one.
	rc = session->put_UserLocale(LCID_EN_US);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to put UserLocale to English", rc);
		return -1;
	}

	// Now we have to get an interface for searching updates. The options are CreateUpdateDownloader, CreateUpdateInstaller, and CreateUpdateSearcher.
	// For more info: https://msdn.microsoft.com/en-us/library/windows/desktop/aa386854(v=vs.85).aspx
	rc = session->CreateUpdateSearcher(&searcher.p);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to create IUpdateSearcher", rc);
		return -1;
	}

	// CreateUpdateSearcher returned an IUpdateSearcher interface. Before we start searching, we should set some attributes.
	// When using COM objects, to set attributes, we call put_[attribute_name], and to get them, we call get_[attribute_name].
	// IUpdateSearcher ref: https://msdn.microsoft.com/en-us/library/windows/desktop/aa386515(v=vs.85).aspx

	if (should_check_online == false)
	{
		// we set the server selection to "Others", since we have added our own internal cab file.
		rc = searcher->put_ServerSelection(ssOthers);
		if (FAILED(rc))
		{
			print_to_stderr("Failed to call IUpdateSearcher::put_ServerSelection", rc);
			return -1;
		}

		// Since we set the server selection to "Others" we need to set our own services. Lets add the service we added before.
		rc = searcher->put_ServiceID(update_service_manager_service_id);
		if (FAILED(rc))
		{
			print_to_stderr("Failed to put service id for searcher", rc);
			return -1;
		}
	}
	else {
		// we set the server selection to ssWindowsUpdate which means getting online.
		rc = searcher->put_ServerSelection(ssWindowsUpdate);
		if (FAILED(rc))
		{
			print_to_stderr("Failed to call IUpdateSearcher::put_ServerSelection", rc);
			return -1;
		}
	}

	// We might have a default value that indicates whether WUA can automatically upgrade when searching. Lets disable it, since we don't
	// wanna change anything.
	rc = searcher->put_CanAutomaticallyUpgradeService(VARIANT_FALSE);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to set can automatically upgrade service to false", rc);
		return -1;
	}

	// Now lets make a search. To just search for all updates (software, drivers, etc) that are not installed we use the follwing filter.
	// ref: https://msdn.microsoft.com/en-us/library/windows/desktop/aa386526(v=vs.85).aspx
	rc = searcher->Search(SysAllocString(L"IsInstalled=0"), &search_result.p);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call IUpdateSearcher::Search", rc);
		return -1;
	}

	// This returned an ISearchResult. Lets validate the ResultCode.
	rc = search_result->get_ResultCode(&search_result_code);
	if (FAILED(rc))
	{
		print_to_stderr("Failed getting result code from search operation", rc);
		return -1;
	}

	if (search_result_code != orcSucceeded)
	{
		// we send here search_result_code even though this isn't an HRESULT. This will result in the print function
		// printing "Unknown Error" but also printing the code itself, which is what important.
		print_to_stderr("Operation Result Code resulted in a non success code", search_result_code);
		return -1;
	}

	// We are all good, lets get the updates.
	rc = search_result->get_Updates(&updateCollection.p);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call ISearchResult::get_Updates", rc);
		return -1;
	}

	// And now, the update count.
	rc = updateCollection->get_Count(&updateCount);
	if (FAILED(rc))
	{
		print_to_stderr("Failed to call IUpdateCollection::get_Count", rc);
		return -1;
	}
	
	for (long i = 0; i < updateCount; i++)
	{
		rc = updateCollection->get_Item(i, &update.p);
		if (FAILED(rc))
		{
			print_to_stderr("Failed to call IUpdateCollection::get_Item", rc);
			return -1;
		}

		rc = get_update(update, &update_list);
		if (rc == -1) {
			return -1;
		}
	}

	// dump the final json. 4 is for pretty dumping (identation etc)
	printf("%s", update_list.dump(4).c_str());
	return 0;
}

int main(int argc, char *argv[])
{
	__try
	{
		_main(argc, argv);
	}
	__except (true)
	{
		printf("AXPM threw an exception. Exiting\n");
		exit(-1);
	}
	return 0;
}