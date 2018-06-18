"""
Uses impacket to implement an interface for remote WUA COM API.
We use the generic IDispatch interface for that.
"""
from utils.com_helper import new_idispatch_from_clsid
import com_interfaces.idispatch
import time

# https://msdn.microsoft.com/en-us/library/ee917961.aspx
CLSID_UpdateSession = "4CB43D7F-7EEE-4906-8698-60DA1C38F2FE"

# Info about all of these values is here:
# https://msdn.microsoft.com/en-us/library/windows/desktop/aa387280(v=vs.85).aspx


class ServerSelectionEnum(object):
    ssDefault = 0
    ssManagedServer = 1
    ssWindowsUpdate = 2
    ssOthers = 3


# https://msdn.microsoft.com/en-us/library/windows/desktop/aa387095(v=vs.85).aspx
class OperationResultCode(object):
    orcNotStarted = 0
    orcInProgress = 1
    orcSucceeded = 2
    orcSucceededWithErrors = 3
    orcFailed = 4
    orcAborted = 5


# https://msdn.microsoft.com/en-us/library/windows/desktop/aa387284(v=vs.85).aspx
class UpdateType(object):
    utSoftware = 1
    utDriver = 2


class RemoteWUAHandler(object):
    def __init__(self, dcom):
        """
        RemoteWUAHandler initializes an IUpdateSession interface on a remote computer, and provides a search_online
        method to search updates on it.
        :param dcom: a DCOMConnection instance.
        """
        self.dcom = dcom
        self.iupdatesession = None

    def search_online(self, search_string):
        """
        Searches for patches in a windows computer. search_string is a string defined by the following
        link: https://msdn.microsoft.com/en-us/library/windows/desktop/aa386526(v=vs.85).aspx
        :param str search_string: a string that defines which patches to look for. e.g.
        ( IsInstalled = 0 and IsHidden = 0 )
        :return:
        """
        self.iupdatesession = new_idispatch_from_clsid(self.dcom, CLSID_UpdateSession)

        # We start with an IUpdateSession interface. Lets create an update searcher.
        i_update_searcher = self.iupdatesession.call("CreateUpdateSearcher", [])

        # IUpdateSearcher is the main interface we are going to work with.
        # Lets configure it to go out online and use Microsoft's WSUS server.
        # hard_check is True to assert the result (since this part is critical)
        i_update_searcher.put("Online", True, hard_check=True)
        i_update_searcher.put("ServerSelection", ServerSelectionEnum.ssWindowsUpdate, hard_check=True)
        i_update_searcher.put("CanAutomaticallyUpgradeService", False, hard_check=True)

        # Now we can search.
        # Search string specs are here: https://msdn.microsoft.com/en-us/library/windows/desktop/aa386526(v=vs.85).aspx
        i_search_result = i_update_searcher.call("Search", [search_string])
        assert type(i_search_result) == com_interfaces.idispatch.IDispatch, \
            "i_search_result is of type {0}".format(type(i_search_result))
        assert i_search_result.get("ResultCode") == OperationResultCode.orcSucceeded

        i_update_collection = i_search_result.get("Updates")

        updates = []

        for i in range(i_update_collection.get("Count")):
            i_update = i_update_collection.get("Item", [i])
            update = dict()
            update['Title'] = i_update.get("Title")
            update['MsrcSeverity'] = i_update.get("MsrcSeverity")
            update['Type'] = i_update.get("Type")

            # Parse Type
            update['Type'] = {
                UpdateType.utDriver: "Driver",
                UpdateType.utSoftware: "Software"
            }.get(update['Type'], "Unknown")

            # Get Categories
            i_category_collection = i_update.get("Categories")
            categories = []
            for c in range(i_category_collection.get("Count")):
                i_category = i_category_collection.get("Item", [c])
                categories.append(i_category.get("Name"))
            update['Categories'] = categories

            # Get KBArticleIDs
            i_string_collection = i_update.get("KBArticleIDs")
            kb_article_ids = []
            for c in range(i_string_collection.get("Count")):
                kb_article_ids.append(i_string_collection.get("Item", [c]))
            update['KBArticleIDs'] = kb_article_ids

            i_string_collection = i_update.get("SecurityBulletinIDs")
            security_bulletin_ids = []
            for c in range(i_string_collection.get("Count")):
                security_bulletin_ids.append(i_string_collection.get("Item", [c]))
            update['SecurityBulletinIDs'] = security_bulletin_ids

            # LastDeploymentChangeTime is the publish date. If we use Microsoft's server (which we use)
            # Then this is the creation time of this patch. But on custom WSUS Servers, this will be the date
            # when this update was installed on the wsus server. Be aware!!
            last_deployment_change_time = i_update.get("LastDeploymentChangeTime")
            # datetime is not json serializable. lets switch to timestamp.
            # later, we can make this a datetime using datetime.fromtimestamp(...)
            update['LastDeploymentChangeTime'] = time.mktime(last_deployment_change_time.timetuple())

            updates.append(update)

        return updates
