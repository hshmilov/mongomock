using System;
using System.Threading;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System.Text;

namespace AXR
{
    class Program
    { 
        static uint MAXIMUM_TIME_FOR_COMMAND_IN_SECONDS = 30;
        static uint MAXIMUM_TIME_FOR_LONG_COMMANDS_IN_SECONDS = 120;

        static AXRCommandOutput ParseCommand(string type, List<string> args)
        {
            AXRCommandOutput result = new AXRCommandOutput();
            result.status = "ok";

            try
            {
                if (type == "shell")
                {
                    var output = Modules.AXRShell.RunShell(args[0]);
                    result.data = JToken.FromObject(output);
                }
                else if (type == "pmonline")
                {
                    result.data = JToken.FromObject(Modules.AXRPM.GetUninstalledSecurityPatches());
                }
                else if (type == "query" || type == "wmiquery")
                {
                    result.data = JToken.FromObject(Modules.AXRWMI.ExecQuery(args[0]));
                }
                else
                {
                    throw new Exception(string.Format("AXR Does not support command {0}", type));
                }

                return result;
            } catch (Exception e)
            {
                return new AXRCommandOutputException(e);
            }
        }

        static void Main(string[] args)
        {
            try
            {
                // Validate Usage
                if (args.Length != 1)
                {
                    throw new Exception(String.Format("Usage: {0} serialized_json / path_to_json_file", AppDomain.CurrentDomain.FriendlyName.ToString()));
                }

                // Parse the input. We try to see if we got a path for a file. If its not, that this must be the actual json.
                List<AXRCommandInput> json_input = null;

                var app_argument = args[0];
                if (File.Exists(app_argument))
                {
                    json_input = JsonConvert.DeserializeObject<List<AXRCommandInput>>(File.ReadAllText(app_argument));
                }
                else
                {
                    // If its a command line paramter, we have to base64-decode it
                    json_input = JsonConvert.DeserializeObject<List<AXRCommandInput>>(Encoding.UTF8.GetString(Convert.FromBase64String(app_argument)));
                }

                // Create the final result object before we start appending output to it
                var final_result = new AXROutput();
                
                // Go over each of the commands and try to run it.
                foreach (var cmd in json_input)
                {
                    AXRCommandOutput result = new AXRCommandOutput();
                    try
                    {
                        // have a timeout on each command
                        var command_thread = new Thread(
                            () =>
                            {
                                result = ParseCommand(cmd.type, cmd.args);
                            }
                            );

                        command_thread.Start();

                        // Some commands are long. Pick up the appropriate timeout.
                        var timeout_for_process = MAXIMUM_TIME_FOR_COMMAND_IN_SECONDS;
                        if (cmd.type == "pmonline") timeout_for_process = MAXIMUM_TIME_FOR_LONG_COMMANDS_IN_SECONDS;

                        if (!command_thread.Join(TimeSpan.FromSeconds(timeout_for_process)))
                        {
                            command_thread.Abort();
                            throw new Exception(String.Format("Timeout {0} seconds", timeout_for_process));
                        }
                    } catch(Exception e)
                    {
                        result = new AXRCommandOutputException(e);
                    }
                    final_result.data.Add(result);
                }

                // Eventually, Append some extra information about this host
                try
                {
                    final_result.hostname = System.Net.Dns.GetHostName();
                } catch (Exception e)
                {
                    final_result.debug.Add(e.ToString());
                }
                final_result.status = "ok";

                // We have to remove "null" values recursively from the object, we don't want to print just empty values.
                // Also other dependencies (our python code) assumes that if a property is null it simply doesn't exist.
                foreach (var final_result_data_row in final_result.data)
                {
                    final_result_data_row.data = JsonHelper.RemoveEmptyChildren(final_result_data_row.data);
                }

                var json_serializer_settings = new JsonSerializerSettings();
                json_serializer_settings.Formatting = Formatting.Indented;
                json_serializer_settings.NullValueHandling = NullValueHandling.Ignore;
                Console.WriteLine(JsonConvert.SerializeObject(final_result, json_serializer_settings));
            } catch (Exception e)
            {
                Console.WriteLine("Exception occured: {0}", e.ToString());
                Environment.Exit(-1);
            }
            // Exit with this api and not return, to ensure that even if we have threads that are stuck, they won't interrupt the exit process
            Environment.Exit(0);
        }
    }
}
