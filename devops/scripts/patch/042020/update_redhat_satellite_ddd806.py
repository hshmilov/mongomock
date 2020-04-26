#!/home/ubuntu/cortex/venv/bin/python

import sys
import subprocess
import base64
import os
import time

from testing.services.plugins import core_service

CORTEX = '/home/ubuntu/cortex'
FILES_TO_UPDATE = {
    f'{CORTEX}/adapters/redhat_satellite_adapter/connection.py': b'aW1wb3J0IGxvZ2dpbmcKZnJvbSBmdW5jdG9vbHMgaW1wb3J0IHBhcnRpYWxtZXRob2QKCmZyb20gdHlwaW5nIGltcG9ydCBEaWN0LCBMaXN0LCBPcHRpb25hbCwgSXRlcmFibGUKCmZyb20gYXhvbml1cy5jbGllbnRzLnJlc3QuY29ubmVjdGlvbiBpbXBvcnQgUkVTVENvbm5lY3Rpb24KZnJvbSBheG9uaXVzLmNsaWVudHMucmVzdC5leGNlcHRpb24gaW1wb3J0IFJFU1RFeGNlcHRpb24KZnJvbSByZWRoYXRfc2F0ZWxsaXRlX2FkYXB0ZXIgaW1wb3J0IGNvbnN0cwoKbG9nZ2VyID0gbG9nZ2luZy5nZXRMb2dnZXIoZidheG9uaXVzLntfX25hbWVfX30nKQoKCmNsYXNzIFJlZGhhdFNhdGVsbGl0ZUNvbm5lY3Rpb24oUkVTVENvbm5lY3Rpb24pOgogICAgIiIiIHJlc3QgY2xpZW50IGZvciBSZWRoYXRTYXRlbGxpdGUgYWRhcHRlciAiIiIKCiAgICBkZWYgX19pbml0X18oc2VsZiwgKmFyZ3MsIGZldGNoX2hvc3RfZmFjdHM6IGJvb2wsIGhvc3RzX2NodW5rX3NpemU6IGludCA9IGNvbnN0cy5ERVZJQ0VfUEVSX1BBR0UsICoqa3dhcmdzKToKICAgICAgICBzdXBlcigpLl9faW5pdF9fKCphcmdzLCB1cmxfYmFzZV9wcmVmaXg9J2FwaScsCiAgICAgICAgICAgICAgICAgICAgICAgICBoZWFkZXJzPXsnQ29udGVudC1UeXBlJzogJ2FwcGxpY2F0aW9uL2pzb24nLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgJ0FjY2VwdCc6ICdhcHBsaWNhdGlvbi9qc29uJ30sCiAgICAgICAgICAgICAgICAgICAgICAgICAqKmt3YXJncykKICAgICAgICBzZWxmLl9mZXRjaF9ob3N0X2ZhY3RzID0gZmV0Y2hfaG9zdF9mYWN0cwogICAgICAgIHNlbGYuX2hvc3RzX2NodW5rX3NpemUgPSBob3N0c19jaHVua19zaXplCgogICAgZGVmIF9jb25uZWN0KHNlbGYpOgogICAgICAgIGlmIG5vdCBzZWxmLl91c2VybmFtZSBvciBub3Qgc2VsZi5fcGFzc3dvcmQ6CiAgICAgICAgICAgIHJhaXNlIFJFU1RFeGNlcHRpb24oJ05vIHVzZXJuYW1lIG9yIHBhc3N3b3JkJykKICAgICAgICAjIHJhaXNlcyBIVFRQRXJyb3IoNDAzLzQwMSkgaWYgdGhlcmUgYXJlIG5vIHBlcm1pc3Npb25zCiAgICAgICAgaG9zdCA9IG5leHQoc2VsZi5faXRlcl9ob3N0cyhsaW1pdD0xLCBzaG91bGRfcmFpc2U9VHJ1ZSksIE5vbmUpCiAgICAgICAgaWYgbm90IGlzaW5zdGFuY2UoaG9zdCwgZGljdCk6CiAgICAgICAgICAgIG1lc3NhZ2UgPSAnSW52YWxpZCBob3N0cyByZXNwb25zZSByZWNlaXZlZCBmcm9tIFNhdGVsbGl0ZSBTZXJ2ZXIuIFBsZWFzZSBjb250YWN0IEF4b25pdXMuJwogICAgICAgICAgICBsb2dnZXIud2FybmluZyhmJ3ttZXNzYWdlfSB7aG9zdH0nKQogICAgICAgICAgICByYWlzZSBFeGNlcHRpb24obWVzc2FnZSkKCiAgICAgICAgIyBvbmx5IGNoZWNrIGZhY3RzIGlmIGl0IHdhcyByZXF1ZXN0ZWQgYW5kIHRoZSBmaXJzdCBob3N0IGhhZCBob3N0X25hbWUKICAgICAgICBpZiBzZWxmLl9mZXRjaF9ob3N0X2ZhY3RzIGFuZCBpc2luc3RhbmNlKGhvc3QuZ2V0KCduYW1lJyksIHN0cik6CiAgICAgICAgICAgIGZhY3RzID0gc2VsZi5fZ2V0KCoqc2VsZi5fcmVxdWVzdF9wYXJhbXNfZm9yX2ZhY3RzX2Zvcl9ob3N0KGhvc3RbJ25hbWUnXSkpCiAgICAgICAgICAgIGlmIG5vdCBpc2luc3RhbmNlKGZhY3RzLCBkaWN0KToKICAgICAgICAgICAgICAgIG1lc3NhZ2UgPSAnSW52YWxpZCBmYWN0cyByZXNwb25zZSByZWNlaXZlZCBmcm9tIFNhdGVsbGl0ZSBTZXJ2ZXIuIFBsZWFzZSBjb250YWN0IEF4b25pdXMuJwogICAgICAgICAgICAgICAgbG9nZ2VyLndhcm5pbmcoZid7bWVzc2FnZX0ge2ZhY3RzfScpCiAgICAgICAgICAgICAgICByYWlzZSBFeGNlcHRpb24obWVzc2FnZSkKCiAgICAjIHB5bGludDogZGlzYWJsZT1hcmd1bWVudHMtZGlmZmVyCiAgICBkZWYgX2RvX3JlcXVlc3Qoc2VsZiwgKmFyZ3MsICoqa3dhcmdzKToKICAgICAgICAjIGlmIG5vdCBpbnN0cnVjdGVkIG90aGVyd2lzZSwgZGVmYXVsdCB0byBiYXNpYyBhdXRoCiAgICAgICAga3dhcmdzLnNldGRlZmF1bHQoJ2RvX2Jhc2ljX2F1dGgnLCBUcnVlKQogICAgICAgIHJldHVybiBzdXBlcigpLl9kb19yZXF1ZXN0KCphcmdzLCAqKmt3YXJncykKCiAgICAjIHB5bGludDogZGlzYWJsZT1hcmd1bWVudHMtZGlmZmVyCiAgICBkZWYgX2hhbmRsZV9yZXNwb25zZShzZWxmLCAqYXJncywgKiprd2FyZ3MpOgogICAgICAgIHJlc3BvbnNlID0gc3VwZXIoKS5faGFuZGxlX3Jlc3BvbnNlKCphcmdzLCAqKmt3YXJncykKICAgICAgICBpZiBpc2luc3RhbmNlKHJlc3BvbnNlLCBkaWN0KToKICAgICAgICAgICAgZXJyb3JfZGljdCA9IHJlc3BvbnNlLmdldCgnZXJyb3InKQogICAgICAgICAgICBpZiBpc2luc3RhbmNlKGVycm9yX2RpY3QsIGRpY3QpOgogICAgICAgICAgICAgICAgcmFpc2UgUkVTVEV4Y2VwdGlvbihmJ1JlZCBIYXQgU2F0ZWxsaXRlIEVycm9yOiB7ZXJyb3JfZGljdH0nKQogICAgICAgIHJldHVybiByZXNwb25zZQoKICAgIGRlZiBfcGFnaW5hdGVkX3JlcXVlc3Qoc2VsZiwgKmFyZ3MsIGxpbWl0OiBPcHRpb25hbFtpbnRdID0gTm9uZSwgc2hvdWxkX3JhaXNlPUZhbHNlLCAqKmt3YXJncyk6CiAgICAgICAgcGFnaW5hdGlvbl9wYXJhbXMgPSBrd2FyZ3Muc2V0ZGVmYXVsdCgKICAgICAgICAgICAgJ3VybF9wYXJhbXMnIGlmIChrd2FyZ3MuZ2V0KCdtZXRob2QnKSBvciBhcmdzWzBdKSA9PSAnR0VUJwogICAgICAgICAgICBlbHNlICdib2R5X3BhcmFtcycsIHt9KQoKICAgICAgICBjaHVua19zaXplID0gc2VsZi5faG9zdHNfY2h1bmtfc2l6ZQogICAgICAgIGlmIGlzaW5zdGFuY2UobGltaXQsIGludCk6CiAgICAgICAgICAgIGNodW5rX3NpemUgPSBtaW4oY2h1bmtfc2l6ZSwgbGltaXQpCiAgICAgICAgcGFnaW5hdGlvbl9wYXJhbXMuc2V0ZGVmYXVsdCgncGVyX3BhZ2UnLCBjaHVua19zaXplKQoKICAgICAgICBjdXJyX3BhZ2UgPSBwYWdpbmF0aW9uX3BhcmFtcy5zZXRkZWZhdWx0KCdwYWdlJywgMSkgICMgcGFnZSBpcyAxLWluZGV4IGJhc2VkCiAgICAgICAgIyBOb3RlOiBpbml0aWFsIHZhbHVlIHVzZWQgb25seSBmb3IgaW5pdGlhbCB3aGlsZSBpdGVyYXRpb24KICAgICAgICB0b3RhbF9jb3VudCA9IGNvdW50X3NvX2ZhciA9IDAKICAgICAgICB0cnk6CiAgICAgICAgICAgIHdoaWxlIGNvdW50X3NvX2ZhciA8PSBtaW4odG90YWxfY291bnQsIGxpbWl0IG9yIGNvbnN0cy5NQVhfTlVNQkVSX09GX0RFVklDRVMpOgogICAgICAgICAgICAgICAgcGFnaW5hdGlvbl9wYXJhbXNbJ3BhZ2UnXSA9IGN1cnJfcGFnZQogICAgICAgICAgICAgICAgcmVzcG9uc2UgPSBzZWxmLl9kb19yZXF1ZXN0KCphcmdzLCAqKmt3YXJncykKCiAgICAgICAgICAgICAgICByZXN1bHRzID0gcmVzcG9uc2UuZ2V0KCdyZXN1bHRzJykKICAgICAgICAgICAgICAgIGlmIG5vdCBpc2luc3RhbmNlKHJlc3VsdHMsIChsaXN0LCBkaWN0KSk6CiAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmVycm9yKGYnSW52YWxpZCByZXN1bHRzIHJldHVybmVkIGFmdGVyIHtjb3VudF9zb19mYXJ9L3t0b3RhbF9jb3VudH06IHtyZXN1bHRzfScpCiAgICAgICAgICAgICAgICAgICAgcmV0dXJuCiAgICAgICAgICAgICAgICBpZiBsZW4ocmVzdWx0cykgPT0gMDoKICAgICAgICAgICAgICAgICAgICBsb2dnZXIuaW5mbyhmJ05vIHJlc3VsdHMgcmV0dXJuZWQgYWZ0ZXIge2NvdW50X3NvX2Zhcn0ve3RvdGFsX2NvdW50fScpCiAgICAgICAgICAgICAgICAgICAgcmV0dXJuCgogICAgICAgICAgICAgICAgaWYgaXNpbnN0YW5jZShyZXN1bHRzLCBkaWN0KToKICAgICAgICAgICAgICAgICAgICB5aWVsZCBmcm9tIHJlc3VsdHMuaXRlbXMoKQogICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICB5aWVsZCBmcm9tIHJlc3VsdHMKCiAgICAgICAgICAgICAgICB0cnk6CiAgICAgICAgICAgICAgICAgICAgY291bnRfc29fZmFyICs9IGxlbihyZXN1bHRzKQogICAgICAgICAgICAgICAgICAgICMgc3VidG90YWwgZGVmaW50aW9uIGZyb20gdGhlIGRvY3VtZW50YXRpb246CiAgICAgICAgICAgICAgICAgICAgIyAgIFRoZSBudW1iZXIgb2Ygb2JqZWN0cyByZXR1cm5lZCB3aXRoIHRoZSBnaXZlbiBzZWFyY2ggcGFyYW1ldGVycy4gSWYgdGhlcmUgaXMgbm8KICAgICAgICAgICAgICAgICAgICAjICAgc2VhcmNoLCB0aGVuIHN1YnRvdGFsIGlzIGVxdWFsIHRvIHRvdGFsLgogICAgICAgICAgICAgICAgICAgIHRvdGFsX2NvdW50ID0gaW50KHJlc3BvbnNlLmdldCgnc3VidG90YWwnKSBvciAwKQogICAgICAgICAgICAgICAgZXhjZXB0IChWYWx1ZUVycm9yLCBUeXBlRXJyb3IpOgogICAgICAgICAgICAgICAgICAgIGxvZ2dlci5leGNlcHRpb24oZidSZWNlaXZlZCBpbnZhbGlkIHBhZ2luYXRpb24gdmFsdWVzIGFmdGVyL29uIHtjb3VudF9zb19mYXJ9L3t0b3RhbF9jb3VudH0nKQogICAgICAgICAgICAgICAgICAgIHJldHVybgoKICAgICAgICAgICAgICAgIGlmIHRvdGFsX2NvdW50IDw9IDA6CiAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmluZm8oZidEb25lIHBhZ2luYXRlZCByZXF1ZXN0IGFmdGVyIHtjb3VudF9zb19mYXJ9L3t0b3RhbF9jb3VudH0nKQogICAgICAgICAgICAgICAgICAgIHJldHVybgoKICAgICAgICAgICAgICAgIGN1cnJfcGFnZSA9IGN1cnJfcGFnZSArIDEKICAgICAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgICAgIGxvZ2dlci5leGNlcHRpb24oZidGYWlsZWQgcGFnaW5hdGVkIHJlcXVlc3QgYWZ0ZXIge2NvdW50X3NvX2Zhcn0ve3RvdGFsX2NvdW50fScpCiAgICAgICAgICAgIGlmIHNob3VsZF9yYWlzZToKICAgICAgICAgICAgICAgIHJhaXNlIGUKCiAgICBwYWdpbmF0ZWRfZ2V0ID0gcGFydGlhbG1ldGhvZChfcGFnaW5hdGVkX3JlcXVlc3QsICdHRVQnKQoKICAgIEBzdGF0aWNtZXRob2QKICAgIGRlZiBfcmVxdWVzdF9wYXJhbXNfZm9yX2ZhY3RzX2Zvcl9ob3N0KGhvc3RfbmFtZSk6CiAgICAgICAgcmV0dXJuIHsnbmFtZSc6IGYndjIvaG9zdHMve2hvc3RfbmFtZX0vZmFjdHMnfQoKICAgIGRlZiBfaXRlcl9hc3luY19mYWN0c19mb3JfaG9zdHMoc2VsZiwgaG9zdF9uYW1lczogSXRlcmFibGVbc3RyXSk6CiAgICAgICAgZmFjdF9yZXF1ZXN0cyA9IHtob3N0X25hbWU6IHNlbGYuX3JlcXVlc3RfcGFyYW1zX2Zvcl9mYWN0c19mb3JfaG9zdChob3N0X25hbWUpIGZvciBob3N0X25hbWUgaW4gaG9zdF9uYW1lc30KCiAgICAgICAgIyBIYW5kbGUgc3VjY2VzZnVsIGZhY3QgcmV0cmlldmFscwogICAgICAgIGZvciByZXNwb25zZSBpbiBzZWxmLl9hc3luY19nZXRfb25seV9nb29kX3Jlc3BvbnNlKGZhY3RfcmVxdWVzdHMudmFsdWVzKCkpOgogICAgICAgICAgICBpZiBub3QgKGlzaW5zdGFuY2UocmVzcG9uc2UsIGRpY3QpIGFuZCBpc2luc3RhbmNlKHJlc3BvbnNlLmdldCgncmVzdWx0cycpLCBkaWN0KSk6CiAgICAgICAgICAgICAgICBsb2dnZXIud2FybmluZyhmJ2ludmFsaWQgcmVzcG9uc2UgcmV0dXJuZWQ6IHtyZXNwb25zZX0nKQogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgZm9yIGhvc3RfbmFtZSwgZmFjdHMgaW4gcmVzcG9uc2VbJ3Jlc3VsdHMnXS5pdGVtcygpOgogICAgICAgICAgICAgICAgaWYgbm90IGZhY3RfcmVxdWVzdHMucG9wKGhvc3RfbmFtZSk6CiAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLndhcm5pbmcoZidjYW5ub3QgZmluZCBob3N0bmFtZSB7aG9zdF9uYW1lfSBpbiByZXF1ZXN0cycpCiAgICAgICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgICAgICB5aWVsZCAoaG9zdF9uYW1lLCBmYWN0cykKCiAgICAgICAgIyBZaWVsZCB0aGUgcmVzdCBvZiB0aGUgaG9zdHMKICAgICAgICBsb2dnZXIuaW5mbyhmJ1RoZSBmb2xsb3dpbmcgaG9zdF9uYW1lcyBkaWQgbm90IHJldHVybiBmYWN0czoge2xpc3QoZmFjdF9yZXF1ZXN0cy5rZXlzKCkpfScpCiAgICAgICAgeWllbGQgZnJvbSAoKGhvc3RfbmFtZSwgTm9uZSkgZm9yIGhvc3RfbmFtZSBpbiBmYWN0X3JlcXVlc3RzLmtleXMoKSkKCiAgICBkZWYgX2l0ZXJfaG9zdHNfYW5kX2ZhY3RzKHNlbGYsIGxpbWl0OiBPcHRpb25hbFtpbnRdPU5vbmUpOgoKICAgICAgICBob3N0c19ieV9ob3N0bmFtZSA9IHt9ICAjIHR5cGU6IERpY3Rbc3RyLCBMaXN0W0RpY3RdXQoKICAgICAgICBkZWYgX2luamVjdF9mYWN0c19hbmRfZmx1c2hfaG9zdHMoKToKICAgICAgICAgICAgaWYgbm90IGhvc3RzX2J5X2hvc3RuYW1lOgogICAgICAgICAgICAgICAgcmV0dXJuCgogICAgICAgICAgICBmb3IgaG9zdF9uYW1lLCBmYWN0c19yZXNwb25zZSBpbiBzZWxmLl9pdGVyX2FzeW5jX2ZhY3RzX2Zvcl9ob3N0cyhob3N0c19ieV9ob3N0bmFtZS5rZXlzKCkpOgogICAgICAgICAgICAgICAgZm9yIGhvc3QgaW4gKGhvc3RzX2J5X2hvc3RuYW1lLnBvcChob3N0X25hbWUsIE5vbmUpIG9yIFtdKToKICAgICAgICAgICAgICAgICAgICAjIE5vdGU6IGZhY3RzX3Jlc3BvbnNlIG1pZ2h0IGJlIE5vbmUgaWYgbm8gZmFjdHMgd2VyZSByZXR1cm5lZCBmb3IgaG9zdF9uYW1lCiAgICAgICAgICAgICAgICAgICAgaG9zdFtjb25zdHMuQVRUUl9JTkpFQ1RFRF9GQUNUU10gPSBmYWN0c19yZXNwb25zZQogICAgICAgICAgICAgICAgICAgIHlpZWxkIGhvc3QKCiAgICAgICAgICAgICMgeWllbGQgdGhlIHJlc3QgaWYgZm9yIHNvbWUgcmVhc29uIG5vdCB5aWVsZGVkIGJ5IHNlbGYuX2l0ZXJfYXN5bmNfZmFjdHNfZm9yX2hvc3RzCiAgICAgICAgICAgICMgTm90ZTogdGhpcyByZWxpZXMgb24gdGhlIGRpY3QucG9wIGFib3ZlIHRvIGNsZWFyIGFueSBob3N0IGZyb20gdGhlIGRpY3QgdGhhdCB3YXMgeWllbGRlZCBieSBmYWN0cwogICAgICAgICAgICBmb3IgaG9zdF9uYW1lLCBob3N0cyBpbiBob3N0c19ieV9ob3N0bmFtZToKICAgICAgICAgICAgICAgIHlpZWxkIGZyb20gaG9zdHMKCiAgICAgICAgZm9yIGksIGhvc3QgaW4gZW51bWVyYXRlKHNlbGYuX2l0ZXJfaG9zdHMobGltaXQ9bGltaXQpKToKICAgICAgICAgICAgaG9zdF9uYW1lID0gaG9zdC5nZXQoJ25hbWUnKQogICAgICAgICAgICBpZiBub3QgaXNpbnN0YW5jZShob3N0X25hbWUsIHN0cik6CiAgICAgICAgICAgICAgICAjIGhvc3RzIHdpdGggbm8gaG9zdG5hbWUgYXJlIHlpZWxkZWQgaGVyZQogICAgICAgICAgICAgICAgeWllbGQgaG9zdAogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgICMgTm90ZTogd2UncmUgcG9wcGluZyB0aGUgaG9zdHMgZm9yIHRoZSBjdXJyZW50IGhvc3RfbmFtZSBiZWNhdXNlIHdlIGRvbnQgbmVlZCB0aGVtIGFueW1vcmUuCiAgICAgICAgICAgIGhvc3RzX2J5X2hvc3RuYW1lLnNldGRlZmF1bHQoaG9zdF9uYW1lLCBbXSkuYXBwZW5kKGhvc3QpCgogICAgICAgICAgICAjIGFmdGVyIGV2ZXJ5IHBhZ2UsIHJ1biB0aGUgZmFjdHMgcmVxdWVzdHMKICAgICAgICAgICAgaWYgKGkgJSBzZWxmLl9ob3N0c19jaHVua19zaXplKSA9PSAwOgogICAgICAgICAgICAgICAgeWllbGQgZnJvbSBfaW5qZWN0X2ZhY3RzX2FuZF9mbHVzaF9ob3N0cygpCgogICAgICAgICMgcGVyZm9ybSBmYWN0cyBpbmplY3Rpb24gYW5kIGZsdXNoIHRoZSByZXN0CiAgICAgICAgeWllbGQgZnJvbSBfaW5qZWN0X2ZhY3RzX2FuZF9mbHVzaF9ob3N0cygpCgogICAgZGVmIF9pdGVyX2hvc3RzKHNlbGYsIGxpbWl0OiBPcHRpb25hbFtpbnRdPU5vbmUsIHNob3VsZF9yYWlzZT1GYWxzZSk6CiAgICAgICAgeWllbGQgZnJvbSBzZWxmLnBhZ2luYXRlZF9nZXQoJ3YyL2hvc3RzJywgbGltaXQ9bGltaXQsIHNob3VsZF9yYWlzZT1zaG91bGRfcmFpc2UpCgogICAgZGVmIGdldF9kZXZpY2VfbGlzdChzZWxmKToKICAgICAgICBpZiBzZWxmLl9mZXRjaF9ob3N0X2ZhY3RzOgogICAgICAgICAgICB5aWVsZCBmcm9tIHNlbGYuX2l0ZXJfaG9zdHNfYW5kX2ZhY3RzKCkKICAgICAgICBlbHNlOgogICAgICAgICAgICB5aWVsZCBmcm9tIHNlbGYuX2l0ZXJfaG9zdHMoKQo=',
    f'{CORTEX}/adapters/redhat_satellite_adapter/consts.py': b'aW1wb3J0IHJlCgpERVZJQ0VfUEVSX1BBR0UgPSAyMDAKTUFYX05VTUJFUl9PRl9ERVZJQ0VTID0gMjAwMDAwMAoKQVRUUl9JTkpFQ1RFRF9GQUNUUyA9ICdzYXRlbGxpdGVfZmFjdHMnCgpWRVJJU09OX0ZJRUxEU19UT19TT0ZUV0FSRV9OQU1FUyA9IHsKICAgICdhdWdlYXN2ZXJzaW9uJzogJ0F1Z2VhcycsCiAgICAnZmFjdGVydmVyc2lvbic6ICdGYWN0ZXInCn0KClJFX0ZJRUxEX05FVF9JTlRFUkZBQ0VfRVhDRVBUX0xPID0gcmUuY29tcGlsZShyJ15uZXRcLmludGVyZmFjZVwuJwogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgcicoPyFsbyknICAjIGV4Y3BldCBmb3IgImxvIiBpbnRlcmZhY2UKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHInKD9QPGludGVyZmFjZV9uYW1lPlteLl0rPylcLicKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHInKD9QPGludGVyZmFjZV9maWVsZD4uKz8pJCcsIHJlLk1VTFRJTElORSkK',
    f'{CORTEX}/adapters/redhat_satellite_adapter/service.py': b'aW1wb3J0IGxvZ2dpbmcKaW1wb3J0IHJlCgpmcm9tIHR5cGluZyBpbXBvcnQgTWF0Y2gKCmZyb20gYXhvbml1cy5hZGFwdGVyX2Jhc2UgaW1wb3J0IEFkYXB0ZXJCYXNlLCBBZGFwdGVyUHJvcGVydHkKZnJvbSBheG9uaXVzLmFkYXB0ZXJfZXhjZXB0aW9ucyBpbXBvcnQgQ2xpZW50Q29ubmVjdGlvbkV4Y2VwdGlvbgpmcm9tIGF4b25pdXMuY2xpZW50cy5yZXN0LmNvbm5lY3Rpb24gaW1wb3J0IFJFU1RDb25uZWN0aW9uCmZyb20gYXhvbml1cy5jbGllbnRzLnJlc3QuY29ubmVjdGlvbiBpbXBvcnQgUkVTVEV4Y2VwdGlvbgpmcm9tIGF4b25pdXMuZGV2aWNlcy5kZXZpY2VfYWRhcHRlciBpbXBvcnQgRGV2aWNlQWRhcHRlcgpmcm9tIGF4b25pdXMuZmllbGRzIGltcG9ydCBGaWVsZCwgTGlzdEZpZWxkCmZyb20gYXhvbml1cy5taXhpbnMuY29uZmlndXJhYmxlIGltcG9ydCBDb25maWd1cmFibGUKZnJvbSBheG9uaXVzLnV0aWxzLmRhdGV0aW1lIGltcG9ydCBwYXJzZV9kYXRlCmZyb20gYXhvbml1cy51dGlscy5maWxlcyBpbXBvcnQgZ2V0X2xvY2FsX2NvbmZpZ19maWxlCmZyb20gcmVkaGF0X3NhdGVsbGl0ZV9hZGFwdGVyIGltcG9ydCBjb25zdHMKZnJvbSByZWRoYXRfc2F0ZWxsaXRlX2FkYXB0ZXIuY29ubmVjdGlvbiBpbXBvcnQgUmVkaGF0U2F0ZWxsaXRlQ29ubmVjdGlvbgpmcm9tIHJlZGhhdF9zYXRlbGxpdGVfYWRhcHRlci5jbGllbnRfaWQgaW1wb3J0IGdldF9jbGllbnRfaWQKCmxvZ2dlciA9IGxvZ2dpbmcuZ2V0TG9nZ2VyKGYnYXhvbml1cy57X19uYW1lX199JykKCgpjbGFzcyBSZWRoYXRTYXRlbGxpdGVBZGFwdGVyKEFkYXB0ZXJCYXNlLCBDb25maWd1cmFibGUpOgogICAgIyBweWxpbnQ6IGRpc2FibGU9dG9vLW1hbnktaW5zdGFuY2UtYXR0cmlidXRlcwogICAgY2xhc3MgTXlEZXZpY2VBZGFwdGVyKERldmljZUFkYXB0ZXIpOgogICAgICAgIGNlcnRfbmFtZSA9IEZpZWxkKHN0ciwgJ0NlcnRpZmljYXRlIE5hbWUnKQogICAgICAgIGVudmlyb25tZW50ID0gRmllbGQoc3RyLCAnRW52aXJvbm1lbnQnKQogICAgICAgIGNhcGFiaWxpdGllcyA9IExpc3RGaWVsZChzdHIsICdDYXBhYmlsaXRpZXMnKQogICAgICAgIGNvbXB1dGVfcHJvZmlsZSA9IEZpZWxkKHN0ciwgJ0NvbXB1dGUgUHJvZmlsZScpCiAgICAgICAgY29tcHV0ZV9yZXNvdXJjZSA9IEZpZWxkKHN0ciwgJ0NvbXB1dGUgUmVzb3VyY2UnKQogICAgICAgIG1lZGl1bSA9IEZpZWxkKHN0ciwgJ01lZGl1bScpCiAgICAgICAgb3JnYW5pemF0aW9uID0gRmllbGQoc3RyLCAnT3JnYW5pemF0aW9uJykKCiAgICBkZWYgX19pbml0X18oc2VsZiwgKmFyZ3MsICoqa3dhcmdzKToKICAgICAgICBzdXBlcigpLl9faW5pdF9fKGNvbmZpZ19maWxlX3BhdGg9Z2V0X2xvY2FsX2NvbmZpZ19maWxlKF9fZmlsZV9fKSwgKmFyZ3MsICoqa3dhcmdzKQoKICAgIEBzdGF0aWNtZXRob2QKICAgIGRlZiBfZ2V0X2NsaWVudF9pZChjbGllbnRfY29uZmlnKToKICAgICAgICByZXR1cm4gZ2V0X2NsaWVudF9pZChjbGllbnRfY29uZmlnKQoKICAgIEBzdGF0aWNtZXRob2QKICAgIGRlZiBfdGVzdF9yZWFjaGFiaWxpdHkoY2xpZW50X2NvbmZpZyk6CiAgICAgICAgcmV0dXJuIFJFU1RDb25uZWN0aW9uLnRlc3RfcmVhY2hhYmlsaXR5KGNsaWVudF9jb25maWcuZ2V0KCdkb21haW4nKSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaHR0cHNfcHJveHk9Y2xpZW50X2NvbmZpZy5nZXQoJ2h0dHBzX3Byb3h5JykpCgogICAgIyBweWxpbnQ6IGRpc2FibGU9YXJndW1lbnRzLWRpZmZlcgogICAgZGVmIGdldF9jb25uZWN0aW9uKHNlbGYsIGNsaWVudF9jb25maWcpOgogICAgICAgIGNvbm5lY3Rpb24gPSBSZWRoYXRTYXRlbGxpdGVDb25uZWN0aW9uKGRvbWFpbj1jbGllbnRfY29uZmlnWydkb21haW4nXSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB2ZXJpZnlfc3NsPWNsaWVudF9jb25maWdbJ3ZlcmlmeV9zc2wnXSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBodHRwc19wcm94eT1jbGllbnRfY29uZmlnLmdldCgnaHR0cHNfcHJveHknKSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB1c2VybmFtZT1jbGllbnRfY29uZmlnWyd1c2VybmFtZSddLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBhc3N3b3JkPWNsaWVudF9jb25maWdbJ3Bhc3N3b3JkJ10sCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmV0Y2hfaG9zdF9mYWN0cz1zZWxmLl9mZXRjaF9ob3N0X2ZhY3RzLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGhvc3RzX2NodW5rX3NpemU9c2VsZi5faG9zdHNfY2h1bmtfc2l6ZSkKICAgICAgICB3aXRoIGNvbm5lY3Rpb246CiAgICAgICAgICAgIHBhc3MKICAgICAgICByZXR1cm4gY29ubmVjdGlvbgoKICAgIGRlZiBfY29ubmVjdF9jbGllbnQoc2VsZiwgY2xpZW50X2NvbmZpZyk6CiAgICAgICAgdHJ5OgogICAgICAgICAgICByZXR1cm4gc2VsZi5nZXRfY29ubmVjdGlvbihjbGllbnRfY29uZmlnKQogICAgICAgIGV4Y2VwdCBSRVNURXhjZXB0aW9uIGFzIGU6CiAgICAgICAgICAgIG1lc3NhZ2UgPSAnRXJyb3IgY29ubmVjdGluZyB0byBjbGllbnQgd2l0aCBkb21haW4gezB9LCByZWFzb246IHsxfScuZm9ybWF0KAogICAgICAgICAgICAgICAgY2xpZW50X2NvbmZpZ1snZG9tYWluJ10sIHN0cihlKSkKICAgICAgICAgICAgbG9nZ2VyLmV4Y2VwdGlvbihtZXNzYWdlKQogICAgICAgICAgICByYWlzZSBDbGllbnRDb25uZWN0aW9uRXhjZXB0aW9uKG1lc3NhZ2UpCgogICAgQHN0YXRpY21ldGhvZAogICAgZGVmIF9xdWVyeV9kZXZpY2VzX2J5X2NsaWVudChjbGllbnRfbmFtZSwgY2xpZW50X2RhdGEpOgogICAgICAgICIiIgogICAgICAgIEdldCBhbGwgZGV2aWNlcyBmcm9tIGEgc3BlY2lmaWMgIGRvbWFpbgoKICAgICAgICA6cGFyYW0gc3RyIGNsaWVudF9uYW1lOiBUaGUgbmFtZSBvZiB0aGUgY2xpZW50CiAgICAgICAgOnBhcmFtIG9iaiBjbGllbnRfZGF0YTogVGhlIGRhdGEgdGhhdCByZXByZXNlbnQgYSBjb25uZWN0aW9uCgogICAgICAgIDpyZXR1cm46IEEganNvbiB3aXRoIGFsbCB0aGUgYXR0cmlidXRlcyByZXR1cm5lZCBmcm9tIHRoZSBTZXJ2ZXIKICAgICAgICAiIiIKICAgICAgICB3aXRoIGNsaWVudF9kYXRhOgogICAgICAgICAgICB5aWVsZCBmcm9tIGNsaWVudF9kYXRhLmdldF9kZXZpY2VfbGlzdCgpCgogICAgQHN0YXRpY21ldGhvZAogICAgZGVmIF9jbGllbnRzX3NjaGVtYSgpOgogICAgICAgICIiIgogICAgICAgIFRoZSBzY2hlbWEgUmVkaGF0U2F0ZWxsaXRlQWRhcHRlciBleHBlY3RzIGZyb20gY29uZmlncwoKICAgICAgICA6cmV0dXJuOiBKU09OIHNjaGVtZQogICAgICAgICIiIgogICAgICAgIHJldHVybiB7CiAgICAgICAgICAgICdpdGVtcyc6IFsKICAgICAgICAgICAgICAgIHsKICAgICAgICAgICAgICAgICAgICAnbmFtZSc6ICdkb21haW4nLAogICAgICAgICAgICAgICAgICAgICd0aXRsZSc6ICdSZWQgSGF0IFNhdGVsbGl0ZS9DYXBzdWxlIERvbWFpbicsCiAgICAgICAgICAgICAgICAgICAgJ3R5cGUnOiAnc3RyaW5nJwogICAgICAgICAgICAgICAgfSwKICAgICAgICAgICAgICAgIHsKICAgICAgICAgICAgICAgICAgICAnbmFtZSc6ICd1c2VybmFtZScsCiAgICAgICAgICAgICAgICAgICAgJ3RpdGxlJzogJ1VzZXIgTmFtZScsCiAgICAgICAgICAgICAgICAgICAgJ3R5cGUnOiAnc3RyaW5nJwogICAgICAgICAgICAgICAgfSwKICAgICAgICAgICAgICAgIHsKICAgICAgICAgICAgICAgICAgICAnbmFtZSc6ICdwYXNzd29yZCcsCiAgICAgICAgICAgICAgICAgICAgJ3RpdGxlJzogJ1Bhc3N3b3JkJywKICAgICAgICAgICAgICAgICAgICAndHlwZSc6ICdzdHJpbmcnLAogICAgICAgICAgICAgICAgICAgICdmb3JtYXQnOiAncGFzc3dvcmQnCiAgICAgICAgICAgICAgICB9LAogICAgICAgICAgICAgICAgewogICAgICAgICAgICAgICAgICAgICduYW1lJzogJ3ZlcmlmeV9zc2wnLAogICAgICAgICAgICAgICAgICAgICd0aXRsZSc6ICdWZXJpZnkgU1NMJywKICAgICAgICAgICAgICAgICAgICAndHlwZSc6ICdib29sJwogICAgICAgICAgICAgICAgfSwKICAgICAgICAgICAgICAgIHsKICAgICAgICAgICAgICAgICAgICAnbmFtZSc6ICdodHRwc19wcm94eScsCiAgICAgICAgICAgICAgICAgICAgJ3RpdGxlJzogJ0hUVFBTIFByb3h5JywKICAgICAgICAgICAgICAgICAgICAndHlwZSc6ICdzdHJpbmcnCiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgIF0sCiAgICAgICAgICAgICdyZXF1aXJlZCc6IFsKICAgICAgICAgICAgICAgICdkb21haW4nLAogICAgICAgICAgICAgICAgJ3VzZXJuYW1lJywKICAgICAgICAgICAgICAgICdwYXNzd29yZCcsCiAgICAgICAgICAgICAgICAndmVyaWZ5X3NzbCcKICAgICAgICAgICAgXSwKICAgICAgICAgICAgJ3R5cGUnOiAnYXJyYXknCiAgICAgICAgfQoKICAgICMgcHlsaW50OiBkaXNhYmxlPXRvby1tYW55LXN0YXRlbWVudHMKICAgIGRlZiBfY3JlYXRlX2RldmljZShzZWxmLCBkZXZpY2VfcmF3KToKICAgICAgICB0cnk6CiAgICAgICAgICAgICMgbm9pbnNwZWN0aW9uIFB5VHlwZUNoZWNrZXIKICAgICAgICAgICAgZGV2aWNlOiBSZWRoYXRTYXRlbGxpdGVBZGFwdGVyLk15RGV2aWNlQWRhcHRlciA9IHNlbGYuX25ld19kZXZpY2VfYWRhcHRlcigpCiAgICAgICAgICAgIGRldmljZV9pZCA9IGRldmljZV9yYXcuZ2V0KCdpZCcpCiAgICAgICAgICAgIGlmIGRldmljZV9pZCBpcyBOb25lOgogICAgICAgICAgICAgICAgbG9nZ2VyLndhcm5pbmcoZidCYWQgZGV2aWNlIHdpdGggbm8gSUQge2RldmljZV9yYXd9JykKICAgICAgICAgICAgICAgIHJldHVybiBOb25lCiAgICAgICAgICAgIGRldmljZS5pZCA9IGRldmljZV9pZAoKICAgICAgICAgICAgIyBnZW5lcmljIGZpZWxkcwogICAgICAgICAgICBkZXZpY2UuaG9zdG5hbWUgPSBkZXZpY2UubmFtZSA9IGRldmljZV9yYXcuZ2V0KCduYW1lJykKICAgICAgICAgICAgZGV2aWNlLmFkZF9pcHNfYW5kX21hY3MoaXBzPVtkZXZpY2VfcmF3LmdldCgnaXAnKV0sIG1hY3M9W2RldmljZV9yYXcuZ2V0KCdtYWMnKV0pCiAgICAgICAgICAgIGRldmljZS5kZXZpY2VfbW9kZWwgPSBkZXZpY2VfcmF3LmdldCgnbW9kZWxfbmFtZScpCiAgICAgICAgICAgIGRldmljZS5kb21haW4gPSBkZXZpY2VfcmF3LmdldCgnZG9tYWluX25hbWUnKQogICAgICAgICAgICBkZXZpY2UucGh5c2ljYWxfbG9jYXRpb24gPSBkZXZpY2VfcmF3LmdldCgnbG9jYXRpb25fbmFtZScpCiAgICAgICAgICAgIGRldmljZS5kZXZpY2Vfc2VyaWFsID0gZGV2aWNlX3Jhdy5nZXQoJ3NlcmlhbCcpCiAgICAgICAgICAgIGRldmljZS51dWlkID0gZGV2aWNlX3Jhdy5nZXQoJ3V1aWQnKQogICAgICAgICAgICBkZXZpY2UuZmlyc3Rfc2VlbiA9IHBhcnNlX2RhdGUoZGV2aWNlX3Jhdy5nZXQoJ2NyZWF0ZWRfYXQnKSkKICAgICAgICAgICAgZGV2aWNlLmxhc3Rfc2VlbiA9IHBhcnNlX2RhdGUoZGV2aWNlX3Jhdy5nZXQoJ3VwZGF0ZWRfYXQnKSkKCiAgICAgICAgICAgIGRldmljZV9hcmNoID0gZGV2aWNlX3Jhdy5nZXQoJ2FyY2hpdGVjdHVyZV9uYW1lJykKICAgICAgICAgICAgb3NfY29tcG9uZW50cyA9IFtkZXZpY2VfYXJjaCwgZGV2aWNlX3Jhdy5nZXQoJ29wZXJhdGluZ3N5c3RlbV9uYW1lJyldCiAgICAgICAgICAgIGZvciB2ZXJzaW9uX2ZpZWxkLCBzb2Z0d2FyZV9uYW1lIGluIGNvbnN0cy5WRVJJU09OX0ZJRUxEU19UT19TT0ZUV0FSRV9OQU1FUy5pdGVtcygpOgogICAgICAgICAgICAgICAgdmVyc2lvbl92YWx1ZSA9IGRldmljZV9yYXcuZ2V0KHZlcnNpb25fZmllbGQpCiAgICAgICAgICAgICAgICBpZiBpc2luc3RhbmNlKHZlcnNpb25fdmFsdWUsIHN0cik6CiAgICAgICAgICAgICAgICAgICAgZGV2aWNlLmFkZF9pbnN0YWxsZWRfc29mdHdhcmUobmFtZT1zb2Z0d2FyZV9uYW1lLCB2ZXJzaW9uPXZlcnNpb25fdmFsdWUsIGFyY2hpdGVjdHVyZT1kZXZpY2VfYXJjaCkKCiAgICAgICAgICAgICMgc3BlY2lmaWMgZmllbGRzCiAgICAgICAgICAgIGRldmljZS5jZXJ0X25hbWUgPSBkZXZpY2VfcmF3LmdldCgnY2VydG5hbWUnKQogICAgICAgICAgICBkZXZpY2UuZW52aXJvbm1lbnQgPSBkZXZpY2VfcmF3LmdldCgnZW52aXJvbm1lbnRfbmFtZScpCiAgICAgICAgICAgIGlmIGlzaW5zdGFuY2UoZGV2aWNlX3Jhdy5nZXQoJ2NhcGFiaWxpdGllcycpLCBsaXN0KToKICAgICAgICAgICAgICAgIGRldmljZS5jYXBhYmlsaXRpZXMgPSBkZXZpY2VfcmF3LmdldCgnY2FwYWJpbGl0aWVzJykKICAgICAgICAgICAgZGV2aWNlLmNvbXB1dGVfcHJvZmlsZSA9IGRldmljZV9yYXcuZ2V0KCdjb21wdXRlX3Byb2ZpbGVfbmFtZScpCiAgICAgICAgICAgIGRldmljZS5jb21wdXRlX3Jlc291cmNlID0gZGV2aWNlX3Jhdy5nZXQoJ2NvbXB1dGVfcmVzb3VyY2VfbmFtZScpCiAgICAgICAgICAgIGRldmljZS5tZWRpdW0gPSBkZXZpY2VfcmF3LmdldCgnbWVkaXVtX25hbWUnKQogICAgICAgICAgICBkZXZpY2Uub3JnYW5pemF0aW9uID0gZGV2aWNlX3Jhdy5nZXQoJ29yZ2FuaXphdGlvbl9uYW1lJykKCiAgICAgICAgICAgICMgZmFjdHMKICAgICAgICAgICAgZGV2aWNlX2ZhY3RzID0gZGV2aWNlX3Jhdy5nZXQoY29uc3RzLkFUVFJfSU5KRUNURURfRkFDVFMpCiAgICAgICAgICAgIGlmIGlzaW5zdGFuY2UoZGV2aWNlX2ZhY3RzLCBkaWN0KToKICAgICAgICAgICAgICAgICMgQ29tbWVudGVkIGZpZWxkcyB0YWtlbiBmcm9tIGh0dHBzOi8vYWNjZXNzLnJlZGhhdC5jb20vc29sdXRpb25zLzE0MDYwMDMKICAgICAgICAgICAgICAgIG1lbW9yeV9zaXplID0gZGV2aWNlX2ZhY3RzLmdldCgnZG1pLm1lbW9yeS5zaXplJykKICAgICAgICAgICAgICAgIGlmIGlzaW5zdGFuY2UobWVtb3J5X3NpemUsIHN0cik6CiAgICAgICAgICAgICAgICAgICAgcmVzID0gcmUuc2VhcmNoKHInKFxkKikgTUInLCBtZW1vcnlfc2l6ZSkKICAgICAgICAgICAgICAgICAgICBpZiByZXM6CiAgICAgICAgICAgICAgICAgICAgICAgIGRldmljZS50b3RhbF9waHlzaWNhbF9tZW1vcnkgPSBpbnQocmVzLmdyb3VwKDEpKSAvIDEwMjQuMAogICAgICAgICAgICAgICAgZGV2aWNlLmJpb3NfdmVyc2lvbiA9IGRldmljZV9mYWN0cy5nZXQoJ2Jpb3NfdmVyc2lvbicpIG9yIGRldmljZV9mYWN0cy5nZXQoJ2RtaS5iaW9zLnZlcnNpb24nKQogICAgICAgICAgICAgICAgIyAibHNjcHUuY3B1X2ZhbWlseSI6ICI2IiwKICAgICAgICAgICAgICAgICMgImxzY3B1LmwxaV9jYWNoZSI6ICIzMksiLAogICAgICAgICAgICAgICAgIyAibHNjcHUubnVtYV9ub2RlKHMpIjogIjEiLAogICAgICAgICAgICAgICAgIyAibHNjcHUubnVtYV9ub2RlMF9jcHUocykiOiAiMCIsCiAgICAgICAgICAgICAgICAjICJsc2NwdS5vbi1saW5lX2NwdShzKV9saXN0IjogIjAiLAogICAgICAgICAgICAgICAgIyAibHNjcHUuc29ja2V0KHMpIjogIjEiLAogICAgICAgICAgICAgICAgIyAibHNjcHUuc3RlcHBpbmciOiAiMyIsCiAgICAgICAgICAgICAgICAjICJsc2NwdS52ZW5kb3JfaWQiOiAiR2VudWluZUludGVsIiwKICAgICAgICAgICAgICAgIGRldmljZS5hZGRfY3B1KGNvcmVzPShpbnQoZGV2aWNlX2ZhY3RzWydsc2NwdS5jcHUocyknXSkKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBpc2luc3RhbmNlKGRldmljZV9mYWN0cy5nZXQoJ2xzY3B1LmNwdShzKScpLCBzdHIpIGVsc2UgTm9uZSksCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICApCiAgICAgICAgICAgICAgICBhZGFwdGVycyA9IHt9CiAgICAgICAgICAgICAgICBmb3IgbWF0Y2hpbmdfZmllbGQgaW4gbWFwKGNvbnN0cy5SRV9GSUVMRF9ORVRfSU5URVJGQUNFX0VYQ0VQVF9MTy5tYXRjaCwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZGV2aWNlX2ZhY3RzLmtleXMoKSk6ICAjIHR5cGU6IE1hdGNoCiAgICAgICAgICAgICAgICAgICAgaWYgbm90IG1hdGNoaW5nX2ZpZWxkOgogICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgICAgICAgICBpbnRlcmZhY2VfbmFtZSwgZmllbGRfbmFtZSA9IHR1cGxlKG1hcChtYXRjaGluZ19maWVsZC5ncm91cGRpY3QoKS5nZXQsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgWydpbnRlcmZhY2VfbmFtZScsICdpbnRlcmZhY2VfZmllbGQnXSkpCiAgICAgICAgICAgICAgICAgICAgaWYgbm90IGFsbChpc2luc3RhbmNlKHZhciwgc3RyKSBmb3IgdmFyIGluIFtpbnRlcmZhY2VfbmFtZSwgZmllbGRfbmFtZV0pOgogICAgICAgICAgICAgICAgICAgICAgICBsb2dnZXIud2FybmluZyhmJ2dvdCBpbnZhbGlkIGludGVyZmFjZSB7bWF0Y2hpbmdfZmllbGQuZ3JvdXAoMCl9JykKICAgICAgICAgICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgICAgICAgICAgYWRhcHRlcnMuc2V0ZGVmYXVsdChpbnRlcmZhY2VfbmFtZSwge30pW2ZpZWxkX25hbWVdID0gZGV2aWNlX2ZhY3RzLmdldChmaWVsZF9uYW1lKQogICAgICAgICAgICAgICAgZm9yIGFkYXB0ZXJfbmFtZSwgZmllbGRzIGluIGFkYXB0ZXJzLml0ZW1zKCk6CiAgICAgICAgICAgICAgICAgICAgZGV2aWNlLmFkZF9uaWMobmFtZT1hZGFwdGVyX25hbWUsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaXBzPVtmaWVsZHMuZ2V0KCdpcHY0X2FkZHJlc3MnKSwgZmllbGRzLmdldCgnaXB2Nl9hZGRyZXNzLmhvc3QnKV0sCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgc3VibmV0cz1bZid7ZmllbGRzLmdldCgiaXB2NF9hZGRyZXNzIil9L3tmaWVsZHMuZ2V0KCJpcHY0X25ldG1hc2siKX0nLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGYne2ZpZWxkcy5nZXQoImlwdjZfYWRkcmVzcy5ob3N0Iil9L3tmaWVsZHMuZ2V0KCJpcHY2X25ldG1hc2suaG9zdCIpfSddKQogICAgICAgICAgICAgICAgZGV2aWNlLmFkZF9pcHNfYW5kX21hY3MoaXBzPVtkZXZpY2VfZmFjdHMuZ2V0KCduZXR3b3JrLmlwdjRfYWRkcmVzcycpXSkKICAgICAgICAgICAgICAgIGRldmljZS5ob3N0bmFtZSA9IGRldmljZS5ob3N0bmFtZSBvciBkZXZpY2VfZmFjdHMuZ2V0KCd1bmFtZS5ub2RlbmFtZScpCiAgICAgICAgICAgICAgICBvc19jb21wb25lbnRzLmFwcGVuZChkZXZpY2VfZmFjdHMuZ2V0KCd1bmFtZS52ZXJzaW9uJykpCiAgICAgICAgICAgICAgICBkZXZpY2UudmlydHVhbF9ob3N0ID0gZGV2aWNlX2ZhY3RzLmdldCgndmlydC5pc19ndWVzdCcpID09ICd0cnVlJwoKICAgICAgICAgICAgIyBub3cgdGhhdCB3ZSd2ZSBjb2xsZWN0ZWQgYWxsIG9zX2NvbXBvbmVudHMgcG9zc2libGUsIGZyb20gaG9zdCBhbmQgaXRzIGZhY3RzLCBmaWd1cmUgb3V0IHRoZSBvcwogICAgICAgICAgICBkZXZpY2UuZmlndXJlX29zKCcgJy5qb2luKGNvbXAgb3IgJycgZm9yIGNvbXAgaW4gb3NfY29tcG9uZW50cykpCgogICAgICAgICAgICBkZXZpY2Uuc2V0X3JhdyhkZXZpY2VfcmF3KQogICAgICAgICAgICByZXR1cm4gZGV2aWNlCiAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICAgICAgbG9nZ2VyLmV4Y2VwdGlvbihmJ1Byb2JsZW0gd2l0aCBmZXRjaGluZyBSZWRoYXRTYXRlbGxpdGUgRGV2aWNlIGZvciB7ZGV2aWNlX3Jhd30nKQogICAgICAgICAgICByZXR1cm4gTm9uZQoKICAgIGRlZiBfcGFyc2VfcmF3X2RhdGEoc2VsZiwgZGV2aWNlc19yYXdfZGF0YSk6CiAgICAgICAgZm9yIGRldmljZV9yYXcgaW4gZGV2aWNlc19yYXdfZGF0YToKICAgICAgICAgICAgZGV2aWNlID0gc2VsZi5fY3JlYXRlX2RldmljZShkZXZpY2VfcmF3KQogICAgICAgICAgICBpZiBkZXZpY2U6CiAgICAgICAgICAgICAgICB5aWVsZCBkZXZpY2UKCiAgICBAY2xhc3NtZXRob2QKICAgIGRlZiBhZGFwdGVyX3Byb3BlcnRpZXMoY2xzKToKICAgICAgICAjIEFVVE9BREFQVEVSIC0gY2hlY2sgaWYgeW91IG5lZWQgdG8gYWRkIG90aGVyIHByb3BlcnRpZXMnCiAgICAgICAgcmV0dXJuIFtBZGFwdGVyUHJvcGVydHkuQXNzZXRzXQoKICAgIEBjbGFzc21ldGhvZAogICAgZGVmIF9kYl9jb25maWdfc2NoZW1hKGNscykgLT4gZGljdDoKICAgICAgICByZXR1cm4gewogICAgICAgICAgICAnaXRlbXMnOiBbCiAgICAgICAgICAgICAgICB7CiAgICAgICAgICAgICAgICAgICAgJ25hbWUnOiAnZmV0Y2hfaG9zdF9mYWN0cycsCiAgICAgICAgICAgICAgICAgICAgJ3RpdGxlJzogJ0ZldGNoIGhvc3QgZmFjdHMnLAogICAgICAgICAgICAgICAgICAgICd0eXBlJzogJ2Jvb2wnLAogICAgICAgICAgICAgICAgfSwKICAgICAgICAgICAgICAgIHsKICAgICAgICAgICAgICAgICAgICAnbmFtZSc6ICdob3N0c19jaHVua19zaXplJywKICAgICAgICAgICAgICAgICAgICAndGl0bGUnOiAnSG9zdCBjaHVuayBzaXplJywKICAgICAgICAgICAgICAgICAgICAnZGVzY3JpcHRpb24nOiAnSG9zdHMgZmV0Y2hpbmcgY2h1bmsgc2l6ZS4nLAogICAgICAgICAgICAgICAgICAgICd0eXBlJzogJ251bWJlcicsCiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgIF0sCiAgICAgICAgICAgICdyZXF1aXJlZCc6IFsnZmV0Y2hfaG9zdF9mYWN0cyddLAogICAgICAgICAgICAncHJldHR5X25hbWUnOiAnUmVkIEhhdCBTYXRlbGxpdGUgQ29uZmlndXJhdGlvbicsCiAgICAgICAgICAgICd0eXBlJzogJ2FycmF5JywKICAgICAgICB9CgogICAgQGNsYXNzbWV0aG9kCiAgICBkZWYgX2RiX2NvbmZpZ19kZWZhdWx0KGNscyk6CiAgICAgICAgcmV0dXJuIHsKICAgICAgICAgICAgJ2ZldGNoX2hvc3RfZmFjdHMnOiBUcnVlLAogICAgICAgICAgICAnaG9zdHNfY2h1bmtfc2l6ZSc6IGNvbnN0cy5ERVZJQ0VfUEVSX1BBR0UsCiAgICAgICAgfQoKICAgIGRlZiBfb25fY29uZmlnX3VwZGF0ZShzZWxmLCBjb25maWcpOgogICAgICAgIHNlbGYuX2ZldGNoX2hvc3RfZmFjdHMgPSBjb25maWcuZ2V0KCdmZXRjaF9ob3N0X2ZhY3RzJywgVHJ1ZSkKICAgICAgICBzZWxmLl9ob3N0c19jaHVua19zaXplID0gY29uZmlnLmdldCgnaG9zdHNfY2h1bmtfc2l6ZScsIGNvbnN0cy5ERVZJQ0VfUEVSX1BBR0UpCg==',
}


def main():
    print(f'Updating Red Hat Satellite to ddd8061ee53d946496f56fcf1d2682bd2123a59a')

    # assert current client
    cs = core_service.CoreService()
    print(f'Current client {cs.node_id}')

    # 1. Backup original
    try:
        for path_to_update in FILES_TO_UPDATE.keys():
            bak_path = f'{path_to_update}.bak'
            if os.path.exists(bak_path):
                os.unlink(bak_path)

        for path_to_update in FILES_TO_UPDATE.keys():
            os.rename(path_to_update, f'{path_to_update}.bak')
    except Exception:
        pass

    # 2. write new files
    for path_to_update, b64_contents in FILES_TO_UPDATE.items():
        with open(path_to_update, 'wb') as f:
            f.write(base64.b64decode(b64_contents))

    # 3. Restart adapter
    for i in range(5):
        try:
            subprocess.check_call('./se.sh re redhat_satellite',
                                  shell=True, cwd=CORTEX)
            print(f'se.sh re succeeded on trial {i}')
            break
        except Exception:
            print(f'Failed se.sh re on trial {i}')
            time.sleep(5)

    try:
        subprocess.check_call('./se.sh af redhat_satellite_adapter_0 --nonblock',
                              shell=True, cwd=CORTEX)
        print(f'se.sh af succeeded')
    except Exception:
        print(f'Failed se.sh af')

    print(f'Done!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
