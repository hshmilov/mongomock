using System;
using Newtonsoft.Json.Linq;
using System.Collections.Generic;
using WUApiLib;
using Newtonsoft.Json;

namespace AXR.Modules
{
    class AXRPM
    {
        // English Locale
        const uint LCID_EN_US = 0x409;

        /// <summary>
        /// Returns a list of uninstalled security patches. Contacts microsoft online.
        /// </summary>
        /// <returns>A list of JObject objects</returns>
        public static List<JObject> GetUninstalledSecurityPatches()
        {
            // Create an update session and set its locale to english
            var updateSession = new UpdateSession();
            updateSession.UserLocale = LCID_EN_US;

            // Now we have to get an interface for searching updates. The options are CreateUpdateDownloader, CreateUpdateInstaller, and CreateUpdateSearcher.
            // For more info: https://msdn.microsoft.com/en-us/library/windows/desktop/aa386854(v=vs.85).aspx
            var updateSearcher = updateSession.CreateUpdateSearcher();

            // We set the server selection to ssWindowsUpdate which means getting update list online.
            updateSearcher.ServerSelection = ServerSelection.ssWindowsUpdate;

            // We might have a default value that indicates whether WUA can automatically upgrade when searching. Lets disable it, since we don't
            // wanna change anything.
            updateSearcher.CanAutomaticallyUpgradeService = false;

            // Now lets make a search. To just search for all updates (software, drivers, etc) that are not installed we use the follwing filter.
            // ref: https://msdn.microsoft.com/en-us/library/windows/desktop/aa386526(v=vs.85).aspx
            var search_result = updateSearcher.Search("IsInstalled=0");

            // Validate that the result code means success
            if (search_result.ResultCode != OperationResultCode.orcSucceeded)
                throw new Exception(string.Format("WUA Search returned a bad result code: {0}", search_result.ResultCode));

            // Now lets go over all updates
            var updates = search_result.Updates;
            var final_updates_list = new List<JObject>();
            for (var update_index = 0; update_index < updates.Count; update_index++)
            {
                var update = updates[update_index];
                var jupdate = new JObject();

                // Get all the information we want about the updates
                jupdate["Title"] = update.Title;
                jupdate["LastDeploymentChangeTime"] = update.LastDeploymentChangeTime;
                
                // Due to how wmi works MsrcSeverity is sometimes an empty string, and this is interpreted as null instead of not existing, so we
                // have to filter it like this.
                if (!String.IsNullOrEmpty(update.MsrcSeverity)) jupdate["MsrcSeverity"] = update.MsrcSeverity;

                if (update.Type == UpdateType.utDriver) jupdate["Type"] = "Driver";
                else if (update.Type == UpdateType.utSoftware) jupdate["Type"] = "Software";

                var categories = new List<string>();
                for (var category_index = 0; category_index < update.Categories.Count; category_index++)
                {
                    categories.Add(update.Categories[category_index].Name);
                }
                jupdate["Categories"] = JToken.FromObject(categories);

                var kb_article_ids = new List<string>();
                for (var kb_i = 0; kb_i < update.KBArticleIDs.Count; kb_i++)
                {
                    kb_article_ids.Add(update.KBArticleIDs[kb_i]);
                }
                jupdate["KBArticleIDs"] = JToken.FromObject(kb_article_ids);

                var security_bulletin_ids = new List<string>();
                for (var sbi = 0; sbi < update.SecurityBulletinIDs.Count; sbi++)
                {
                    security_bulletin_ids.Add(update.SecurityBulletinIDs[sbi]);
                }
                jupdate["SecurityBulletinIDs"] = JToken.FromObject(security_bulletin_ids);

                // Finally, add this update to the list of updates
                final_updates_list.Add(jupdate);
            }

            return final_updates_list;
        }
    }
}
