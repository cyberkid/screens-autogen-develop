import pprint
import copy

import requests
import json


# This is the library that can fetch a facebook feed
# The screen_config has a specific "source_info" block which specifies the required fields
# "source" is the specification for the URL of the feed
#

# For example
#   {
#      "name" : "Facebook-MarchMadness",
#      "fetcher" : "facebook",
#      "furl_generator" : "embedly_rss",
#      "app" : "facebook",
#      "grouping" : "facebook",
#      "source" : "https://graph.facebook.com/v2.2/176134773759/feed?access_token=1021790844549388|iK2pnIeExkb_XiUVsNpJxaMj0cs",
#      "post_url" : "https://www.facebook.com/NCAAMarchMadness/posts/{}",
#      "enabled" : true,
#      "tags" : ["Social"],
#      "max_items" : 20,
#      "skip" : 0
#    },

# This script will fetch the facebook feed, then put it into an array of "results"

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

    results_t = process_facebook(source_info, options, debug)

    min = 0
    max = None
    if 'skip' in source_info:
        min = source_info['skip']

    if 'max_items' in source_info:
        max = source_info['max_items'] + min

    results = results_t[min:max]

    return results


def process_facebook(source_info, options, debug):
    """
    we fetch the source and then process it

    :param source_info: Information about the facebook feed source
    :param options: Any options passed in
    :param debug: If true, print additional debugging info
    :return: A list of items extracted from the feed, that can be further processed to make furls
    """

    tags = source_info.get('tags')
    name = source_info.get('name')
    post_url = source_info.get("post_url")
    category = ""

    if not post_url:
        print("ERROR in facebook configuration: Need post url")
        return []

    facebook_source = source_info['source']

    if debug:
        print(u"Processing facebook feed source for:")
        pprint.pprint(source_info)
        print(u"Fetching facebook feed source from: {}".format(facebook_source).encode("utf-8"))

    data = requests.get(facebook_source)
    data_json = json.loads(data.content)
    posts = data_json["data"]

    results = []
    rank = 0
    for post in posts:
        message = extract_field(post, "message", debug)

        created_time = extract_field(post, "created_time", debug)

        id = extract_field(post, "id", debug)

        link = make_post_link(id, post_url)

        all_tags = copy.copy(tags)

        result = {
            "RID" : unicode(rank) + ":" + name,
            "title" : message,
            "date" : created_time,
            "description" : clean_description(message, num_chars = 100),
            "guid" : id,
            "link" : link,
            "category" : category,
            "tags" : all_tags
        }

        results.append(result)

        rank += 1

    return results


def make_post_link(facebook_id, post_url):
    parts = facebook_id.split("_")
    id = parts[1]
    return unicode(post_url).format(id).encode("utf-8")


def extract_field(feed_entry, field_name, debug):
    """
    Extract field value from a facebook feed entry
    Reference: https://pythonhosted.org/feedparser/basic-existence.html

    :param feed_entry: facebook feed entry
    :param field_name: Name of the field in facebook feed entry
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
