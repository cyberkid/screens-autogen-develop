import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import copy
import pprint

from fetchers import fetcher_RSS

from furl_generators import furl_generator_embedly_rss

from optparse import OptionParser
# lets make a source_data
if __name__ == "__main__":
    debug = 0
    #global debug

    parser = OptionParser()
    parser.add_option("-o", "--outfile", dest="out_file", help="write screen output to outputfile")
    parser.add_option("-d", "--debug",
                    action="store_true", dest="debug", default=False,
                help="enable debug")
    parser.add_option("-c", "--cfg_file", dest="cfg_file",
                      help="the screens config file to load")
    parser.add_option("-t", "--test_run", dest="test_run", action="store_true", default=False)
    parser.add_option("-x", dest="rss_local")
    parser.add_option("-p", "--prefetch", dest="prefetch", action="store_true", default=False,
                      help="prefetch the cloud-functions in the generated screen from canary")

    (options, args) = parser.parse_args()

    if options.debug:
        debug = 1

    if debug:
        print(u"Debug is enabled")


    source_info = {
        "name": "my_test_feed1",
        "fetcher" : "RSS",
        "source" : "http://feeds.feedburner.com/TechCrunch/",
        "enabled" : True,
        "tags" : ["tag1", "tag2"],
        "skip" : 0,
        "max_items" : 10,
        "furl_generator" : "embedly"
    }


    results_1 = fetcher_RSS.fetch(source_info, options)

    print(u"Results before FURL-generator:")
    pprint.pprint(results_1)

    results_2 = copy.deepcopy(results_1)

    furl_generator_embedly_rss.add_furls(results_2, debug)

    print(u"Results after FURL-generator:")
    pprint.pprint(results_2)

    source_info["source"] = "test_rss_malformed_item.xml"
    results_t = fetcher_RSS.process_rss(source_info, options, debug)

    print(u"Results after processing rss from test_rss1.xml:")
    pprint.pprint(results_t)
