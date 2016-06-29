import pprint
import copy
import requests
import re
#from urllib2 import urlopen
from lxml.html import fromstring


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

    results_t = process_css(source_info, options, debug)

    min = 0
    max = None
    if 'skip' in source_info:
        min = source_info['skip']

    if 'max_items' in source_info:
        max = source_info['max_items'] + min

    results = results_t[min:max]

    return results


def process_css(source_info, options, debug):

    # we fetch the URL and then apply the css_selector in "selector"
    tags = source_info.get('tags')
    name = source_info.get('name')
    category = ""

    html = ""
    if options.rss_local:
        html_source = options.rss_local + "/" + name + ".html"
    else:
        html_source = source_info['source']

    if debug:
        print(u"Processing css_selector fetcher for:")
        pprint.pprint(source_info)
        print(u"Fetching html from: {}".format(html_source).encode("utf-8"))

    if options.rss_local:
        with open(html_source, "r") as IN:
            html = IN.read()
    else:
        # we fetch the HTML via the web

        # lets load the html
        #user_agent = {"User-agent" : userAgent}
        agent=source_info.get("user_agent", USER_AGENT)
        user_agent = {"User-agent" : agent}
        r = requests.get(html_source, headers = user_agent)
        html = r.text


    dom = fromstring(html)
    dom.make_links_absolute(html_source)
    css_selector = source_info['selector']
    init_results = dom.cssselect(css_selector)

    results = []
    rank = 0
    for element in init_results:
        #if 'href' not in element.keys:
        #    continue

        all_tags = copy.copy(tags)
        url = element.attrib['href']
        result = {
            "RID" : unicode(rank) + ":" + name,
            "url" : url,
            "tags" : all_tags,
            "text" : element.text_content()
        }

        results.append(result)

    return results

