using Newtonsoft.Json;
using System.Collections.Generic;

namespace AXR
{
    class AXROutput
    {
        [JsonProperty(Required = Required.Always)]
        public string status { get; set; }

        [JsonProperty(Required = Required.Always)]
        public List<AXRCommandOutput> data { get; set; } = new List<AXRCommandOutput>();

        // The following are optional
        public string hostname { get; set; }
        public List<string> debug { get; set; } = new List<string>();
    }
}
