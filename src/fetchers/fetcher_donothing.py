import pprint
import copy
import requests
import re
import time

# This is the library that can fetch a URL and apply a css selector to it
# http://arunrocks.com/easy-practical-web-scraping-in-python/
#

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36"


def fetch(source_info, options, debug = 0):
    # We fetch the stuff and add to RESULTS
    if debug:
        print(u"Debug is enabled, called fetchFeed with source info: <{}>".format(source_info).encode("utf-8"))

    # now lets fetch the page
    if not debug and options.debug:
        debug = 1

    results_t = []
    sleep_time = 120
    if "sleeptime" in source_info:
        sleep_time = int(source_info['sleeptime'])
    print("In fetcher do_nothing, sleeping {} seconds".format(sleep_time))
    time.sleep(sleep_time)


    return results_t
