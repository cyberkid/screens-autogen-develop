import pprint
import copy
import requests
import re

# This is the library that can fetch a "feed" from a Bleacherreport URL from an HTML
#
# example: http://bleacherreport.com/articles/2618335-kentucky-vs-texas-am-score-highlights-and-reaction-from-2016-regular-season

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36"


def clean_description(text, num_chars=100):
    # we will limit it to n characters (could be smarter and keep a word boundary
    text = (text[:num_chars] + '..') if len(text) > num_chars else text
    return text


def fetch(source_info, options, debug = 0):
    # We fetch the stuff and add to RESULTS
    if debug:
        print(u"Debug is enabled, called fetchFeed with source info: <{}>".format(source_info).encode("utf-8"))

    # now lets fetch the page
    if not debug and options.debug:
        debug = 1

    results_t = process_toi(source_info, options, debug)

    min = 0
    max = None
    if 'skip' in source_info:
        min = source_info['skip']

    if 'max_items' in source_info:
        max = source_info['max_items'] + min

    results = results_t[min:max]

    return results


def process_toi(source_info, options, debug):
    """
    we fetch the source and then use regex to extract the URLs and IDs we want

    :param source_info: Information about the furl source (RSS feed in this case)
    :param options: Any options passed in
    :param debug: If true, print additional debugging info
    :return: A list of items extracted from the html, that can be further processed to make furls
    """

    tags = source_info.get('tags')
    name = source_info.get('name')
    category = ""

    html = ""
    if options.rss_local:
        html_source = options.rss_local + "/" + name + ".html"
    else:
        html_source = source_info['source']

    if debug:
        print(u"Processing TOI fetcher for:")
        pprint.pprint(source_info)
        print(u"Fetching TOI from: {}".format(html_source).encode("utf-8"))

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


    # now lets parse the html
    results = []
    rank = 0


    # There are two separators:
    # <div class="section">  and then after that <div class="clr">

    chunks = re.split('<div class="item hentry">', html)

    # we drop the first item (before the first match)
    chunks.pop(0)

    for chunk in chunks:

        #print("##### Got chunk: <{}>".format(chunk))
        title = ""
        url = ""

        # the URL is super easy
        m = re.search("href=\"([^\"]+)", chunk)
        if m:
            url = m.group(1)
        else:
            if options.debug:
                print("Failed to match a cosmopolitan URL in chunk: <{}> source: <{}>".format(chunk, html_source))

        all_tags = copy.copy(tags)

        result = {
            "RID" : unicode(rank) + ":" + name,
            "title" : title,
            "url" : url,
            "tags" : all_tags
        }

        keep = 1
        # lets check for the filterout
        if "filterout" in source_info:
            # we iterate across each field and if any of those items are present then we drop it!
            for entry in source_info['filterout']:
                key = entry.keys()[0]
                value = entry[key]
                m = re.search(value, result[key])
                if m:
                    # we matched the negative filter...
                    if options.debug:
                        print("Matched: <{}> in <{}>, filteringout!".format(value, result[key]))
                    keep = 0
                    break
        if keep and url:
            results.append(result)
            rank += 1

    return results

