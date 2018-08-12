using Newtonsoft.Json;
using System.Collections.Generic;

namespace AXR
{
    class AXRCommandInput
    {
        [JsonProperty(Required = Required.Always)]
        public string type { get; set; }

        [JsonProperty(Required = Required.Always)]
        public List<string> args { get; set; }
    }
}
