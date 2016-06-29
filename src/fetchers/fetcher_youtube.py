import pprint
import copy
import requests
import re

# This is the library that can fetch an a Youtube feed from an HTML
# RECOMMENEDED USE RSS and the channel_id if it works, this is only for cases that don't normally work!

# This script will fetch the html page and add the YouTube ID and YouTube URL, then put it into an array of "results"

# example: https://www.youtube.com/channel/UC7EY-H9hmOcrckQ1X-I6SpA/videos

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

    results_t = process_youtube(source_info, options, debug)

    min = 0
    max = None
    if 'skip' in source_info:
        min = source_info['skip']

    if 'max_items' in source_info:
        max = source_info['max_items'] + min

    results = results_t[min:max]

    return results


def process_youtube(source_info, options, debug):
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
        print(u"Processing youtube fetcher for:")
        pprint.pprint(source_info)
        print(u"Fetching youtube from: {}".format(html_source).encode("utf-8"))

    if options.rss_local:
        with open(html_source, "r") as IN:
            html = IN.read()
    else:
        # we fetch the HTML via the web

        # lets load the html
        #user_agent = {"User-agent" : userAgent}
        agent=source_info.get("user_agent", USER_AGENT)
        user_agent = {"User-agent" : agent}
        r = requests.get(html_source, headers = user_agent, verify=False)
        html = r.text


# now lets parse the html
    results = []
    rank = 0
    # we split on <div class="yt-lockup-content">
    chunks = re.split('<div class="yt-lockup-content">', html)
    # we drop the first item
    chunks.pop(0)
    for chunk in chunks:

        # we want the youtube_id
        #<h3 class="yt-lockup-title "><a class="yt-uix-sessionlink yt-uix-tile-link  spf-link  yt-ui-ellipsis yt-ui-ellipsis-2" dir="ltr" title="Kentucky vs Texas A&amp;M basketball 20 Feb 2016"  aria-describedby="description-id-897306" data-sessionlink="feature=c4-videos&amp;ei=5HnLVsSgF4Lg-gOshpmwCw&amp;ved=CDAQvxsiEwjEorTlpIzLAhUCsH4KHSxDBrYomxw" href="/watch?v=IXWbde5hTgs">Kentucky vs Texas A&amp;M basketball 20 Feb 2016</a><span class="accessible-description" id="description-id-897306"> - Duration: 1 hour, 52 minutes.</span></h3>
        title = ""
        youtube_id = ""
        youtube_url = ""
        description = ""

        # skip ads:
        m = re.search('aria-label="Advertisement">Ad</span>', chunk)
        if m:
            if options.debug:
                print("Skipping youtube add for chunk...")
            continue


        m = re.search(" title=\"([^\"]+)\"", chunk)
        if m:
            title = m.group(1)
        else:
            print("Failed to match a YouTube title in chunk: <{}> source: <{}>".format(chunk, html_source))

        # youtube_id, URL:
        m = re.search("href=\"\/watch\?v=([^\"]+)\"", chunk)
        if m:
            youtube_id = m.group(1)
            youtube_url = "https://www.youtube.com/watch?v=" + youtube_id
        else:
            print("Failed to match a YouTube id in chunk: <{}> source: <{}>".format(chunk, html_source))

        # lets try to get the description
        m = re.search('<div class="yt-lockup-description yt-ui-ellipsis yt-ui-ellipsis-2" dir="ltr">([\S\s]*?)</div>', chunk)
        if m:
            description = m.group(1)
        else:
            if 0: # description is optional!
                print("Failed to match a YouTube description in chunk: <{}> source: <{}>".format(chunk, html_source))

        all_tags = copy.copy(tags)

        result = {
            "RID" : unicode(rank) + ":" + name,
            "title" : title,
            "youtube_id" : youtube_id,
            "url" : youtube_url,
            "description" : description,
            "tags" : all_tags
        }

        if youtube_url:
            results.append(result)
            rank += 1

    return results

