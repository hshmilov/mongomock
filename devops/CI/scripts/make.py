"""
Builds a docker image, pushes it to our cloud registry, run tests, etc.
In general, this should be used on each repository that is a plugin/adapter, including core, gui, etc.
"""
import sys
from teamcity.messages import TeamcityServiceMessages

def main():
    # Initialize TeamcityServiceMessages. They output messages that teamcity can read.
    tc = TeamcityServiceMessages()

    with tc.block("hello world block 1"):
        with tc.block("hello world block 2"):
            with tc.block("doing progress"):
                tc.customMessage("text", "status")

if __name__ == '__main__':
    sys.exit(main())
