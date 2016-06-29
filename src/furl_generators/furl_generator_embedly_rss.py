import urllib

__author__ = 'ericglover'


def add_furls(results, debug=0):
    # this will scan each result and add a FURL

    for result in results:
        # RSS has a link and a guid
        # typically we want to use the link, but if the link is not "good enough" we use the guid
        if 'url' in result:
            url = result['url']
            FURL = "func://quixey.com/cloudSearch-showWeb?url=" + urllib.quote(url.encode("utf8"))
            result['furl'] = FURL
        else:
            url_to_use = result['link']
            if len(url_to_use) < 20:
                url_to_use = result['guid']

            FURL = "func://quixey.com/cloudSearch-showWeb?url=" + urllib.quote(url_to_use.encode("utf8"))
            result['furl'] = FURL
            if 'url' not in result:
                result['url'] = url_to_use