using System;

namespace AXR.Modules
{
    class AXRShell
    {
        public static string RunShell(string command)
        {
            System.Diagnostics.ProcessStartInfo procStartInfo =
                new System.Diagnostics.ProcessStartInfo("cmd", "/c " + command);

            // The following commands are needed to redirect the standard output.
            // This means that it will be redirected to the Process.StandardOutput StreamReader.
            procStartInfo.RedirectStandardOutput = true;
            procStartInfo.RedirectStandardError = true;

            // Set this to false, ShellExecute is True when we want to use the ShellExecute APi rather than the CreateProcess one.
            procStartInfo.UseShellExecute = false;

            // Do not create the black window.
            procStartInfo.CreateNoWindow = true;

            // Now we create a process, assign its ProcessStartInfo and start it
            System.Diagnostics.Process proc = new System.Diagnostics.Process();
            proc.StartInfo = procStartInfo;
            proc.Start();

            // We have to read the output now and not wait for the exit! if we are going to have too much output the buffer is going to be full, this will
            // result in a deadlock.
            // Regarding timeout - the context above us (the actual program) takes care of it, no need for a timeout here.
            return proc.StandardOutput.ReadToEnd() + proc.StandardError.ReadToEnd();
        }
    }
}
