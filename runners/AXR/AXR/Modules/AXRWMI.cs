using Newtonsoft.Json.Linq;
using System.Collections.Generic;
using WbemScripting;

namespace AXR.Modules
{
    class AXRWMI
    {
        static SWbemServices sWbemServices = null;
        /// <summary>
        /// Executes a WQL statement and returns a list of jobjects representing the answers.
        /// </summary>
        /// <param name="wql_query">a wql string</param>
        /// <returns>A List of JObjects with all the attributes</returns>
        public static List<JObject> ExecQuery(string wql_query)
        {
            // Connect to localhost (in terms of wmi) and get the SWbemServices interface. 
            if (sWbemServices == null)
            {
                var s_wbem_locator = new SWbemLocator();
                sWbemServices = s_wbem_locator.ConnectServer(
                    strNamespace: "ROOT\\CIMV2",
                    strLocale: "MS_409",    // English Locale
                    iSecurityFlags: (int)WbemConnectOptionsEnum.wbemConnectFlagUseMaxWait  // Give up after 2 minutes (Max Timeout)
                    );
            }

            var wql_raw_result = sWbemServices.ExecQuery(wql_query, iFlags: (int) (WbemFlagEnum.wbemFlagForwardOnly | WbemFlagEnum.wbemFlagReturnImmediately));
            var wql_enumerator = wql_raw_result.GetEnumerator();

            var j_rows = new List<JObject>();

            while (wql_enumerator.MoveNext())
            {
                SWbemObject wql_current_row = (SWbemObject) wql_enumerator.Current;
                JObject j_current_row = new JObject();

                // Lets go over all properties
                var property_enumerator = wql_current_row.Properties_.GetEnumerator();
                while (property_enumerator.MoveNext())
                {
                    var swbem_property = (SWbemProperty) property_enumerator.Current;
                    var pname = swbem_property.Name;
                    var pvalue = JToken.FromObject(swbem_property.get_Value());

                    j_current_row[pname] = pvalue;
                }

                j_rows.Add(j_current_row);
            }

            return j_rows;
        }
    }
}
