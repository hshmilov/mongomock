using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System;
using System.Collections.Generic;

namespace AXR
{
    class AXRCommandOutput
    {
        [JsonProperty(Required = Required.Always)]
        public string status { get; set; }

        // This could be anything. On excpetion, it would be a string. Otherwise it would usually be a list of properties.
        [JsonProperty(Required = Required.Always)]
        public JToken data { get; set; }
    }

    class AXRCommandOutputException : AXRCommandOutput
    {
        public AXRCommandOutputException(Exception e)
        {
            this.status = "exception";
            this.data = JToken.FromObject(e.ToString());
        }
    }
}
