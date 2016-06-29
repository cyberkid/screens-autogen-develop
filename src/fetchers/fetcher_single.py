import pprint
import copy

import feedparser


# This is the library that builds a feed from just the "single" FURL specified

# For example
#   {
#      "name":"Yahoo-weather-delhi",
#      "fetcher":"single",
#      "app":"weather.yahoo.com",
#      "grouping":"weather",
#      "furl_generator" : "null",
#      "furl" : "func://weather.yahoo.com/showWeatherAtCity/mumbai",
#      "url" : "",
#      "enabled" : true,
#      "tags" : ["Mumbai"]
#    },

# This script will just build the result and return it!

def fetch(source_info, options, debug = 0):
    result = {
        "app" : source_info["app"],
        "furl" : source_info["furl"],
        "url" : source_info['url'],
        "tags" : source_info['tags']
    }
    results = [result]
    return results

