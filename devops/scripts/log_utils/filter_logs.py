#!/usr/bin/env python3
"""
Filters logs that come from clients. We filter errors by types and save them sorted to different files.
Open files in "html syntax" mode to make it easier for you to expand and collapse log blocks
"""
import sys
import json
import datetime
from dateutil.parser import parse


def main():
    try:
        _, filename = sys.argv
    except Exception:
        print(f"Usage: {sys.argv[0]} logpath.log")

    log_types = {}

    with open(filename, "rt") as f:
        content = f.read()
        for i, line in enumerate(content.splitlines()):
            log = json.loads(line)
            log_level = log.get("level", "")
            log_message = log.get("message", "")
            log_timestamp = parse(log.get("@timestamp", "00:00"))
            log_funcname, log_linenumber = log.get("funcName", ""), log.get("lineNumber", "")
            log_filename = log.get("filename", "")
            log_exc_info = log.get("exc_info", "").replace('\\\\', '\\')

            if log_level not in log_types:
                log_types[log_level] = []

            msg = f"<{i}>\n"
            msg += f"{log_timestamp.hour}:{log_timestamp.minute} - {log_filename}:{log_funcname}:{log_linenumber}\n" \
                   f"{log_message}\n".replace(">", "/>")
            if log_exc_info != "":
                msg += f"Exception: {log_exc_info}\n"
            msg += f"</{i}>"

            log_types[log_level].append(msg)

        for log_level, log_list in log_types.items():
            with open(f"{filename}.{log_level}", "wt") as f:
                f.write("\n\n".join(log_list))


if __name__ == '__main__':
    sys.exit(main())
