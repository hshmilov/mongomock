DEFAULT_PORT = 8001

# The documentation never stays what is the limit per request. But I tried a huge value and the error said
# the maximum i can get here is 100. Since this can change (no documentation says something else)
# I will make this a smaller number.
INSTANCES_QUERY_RATE = 80
