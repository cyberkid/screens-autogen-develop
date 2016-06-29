import pprint
import copy

import feedparser
import socket

timeout = 20
socket.setdefaulttimeout(timeout)


# This is the library that can fetch an RSS or Atom feed
# The screen_config has a specific "source_info" block which specifies the required fields
# "source" is the specification for the URL of the feed
#

# For example
#   {
#      "name":"TechCrunch-main",
#      "fetcher":"RSS",
#      "app":"techcrunch",
#      "furl_generator" : "embedly",
#      "source" : "http://feeds.feedburner.com/TechCrunch/",
#      "enabled" : true,
#      "tags" : ["Biz"],
#      "parameters" : "wc",
#      "max_items" : 10,
#      "skip" : 0
#    },

# This script will fetch the RSS, then put it into an array of "results" with the fields typical of an RSS

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

    results_t = process_rss(source_info, options, debug)

    min = 0
    max = None
    if 'skip' in source_info:
        min = source_info['skip']

    if 'max_items' in source_info:
        max = source_info['max_items'] + min

    results = results_t[min:max]

    return results


def process_rss(source_info, options, debug):
    """
    we fetch the source and then process it specific for RSS

    :param xml: XML data extracted from RSS feed
    :param source_info: Information about the furl source (RSS feed in this case)
    :param options: Any options passed in
    :param debug: If true, print additional debugging info
    :return: A list of items extracted from RSS, that can be further processed to make furls
    """

    tags = source_info.get('tags')
    name = source_info.get('name')
    category = ""

    if options.rss_local:
        rss_source = options.rss_local + "/" + name + ".rss"
    else:
        rss_source = source_info['source']

    if debug:
        print(u"Processing RSS for:")
        pprint.pprint(source_info)
        print(u"Fetching RSS from: {}".format(rss_source).encode("utf-8"))

    data = feedparser.parse(
        rss_source,
        agent=source_info.get("user_agent", USER_AGENT)
    )

    results = []
    rank = 0
    for feed_entry in data.entries:
        title = extract_field(feed_entry, "title", debug)

        published_date = extract_field(feed_entry, "published", debug)

        summary = extract_field(feed_entry, "summary", debug)

        id = extract_field(feed_entry, "id", debug)

        link = feed_entry.get("link", "")
        if not link:
            links = feed_entry.get("links", "")
            if links and isinstance(links, list):
                link = links[0].get('href')
        if debug:
            if link:
                print(u"Got link: <{}>".format(link).encode("utf-8"))
            else:
                print(u"No link")

        all_tags = copy.copy(tags)

        result = {
            "RID" : unicode(rank) + ":" + name,
            "title" : title,
            "date" : published_date,
            "description" : clean_description(summary, num_chars = 100),
            "guid" : id,
            "link" : link,
            "category" : category,
            "tags" : all_tags
        }

        results.append(result)

        rank += 1

    return results


def extract_field(feed_entry, field_name, debug):
    """
    Extract field value from an RSS entry
    Reference: https://pythonhosted.org/feedparser/basic-existence.html

    :param feed_entry: RSS entry
    :param field_name: Name of the field in RSS entry
    :param debug: Print debugging info or not
    :return: Value of the field or empty string if the field is absent
    """

    field_value = feed_entry.get(field_name, "")
    if debug:
        if field_value:
            print(u"Got {}: <{}>".format(field_name, field_value).encode("utf-8"))
        else:
            print(u"No {}".format(field_name).encode("utf-8"))
    return field_value
