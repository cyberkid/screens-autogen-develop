import json
import codecs
import gzip
import os
import re

__author__ = 'ericglover'


include_url = False
# Functions:
# build_screen(all_screen_data, screen_cfg_data, options, debug = 0)

def build_screen(screen_result_data, screen_cfg_data, options):
    """
    # loads the base_cfg_file
    # builds the structures for the card-list-widgets
    # appends the new data
    # writes out the output screen-file (json) to the specified location
    # writes out the file in gzip format as well if required

    :param screen_result_data:
    :param screen_cfg_data:
    :param options:
    :return:
    """

    debug = 0
    if options.debug:
        print(u"in Screen builder: build_screen")
        debug = 1

    output_path = options.output_path
    screen_file_name = os.path.join(output_path, screen_cfg_data['screen-file-name'])
    screen_config_file = screen_cfg_data['screen-config-base']
    screen_child_uuid = ""
    m = re.search("^([a-f0-9\-]+)\.json", screen_cfg_data['screen-file-name'])
    if not m:
        print("########\n########\nWARNING: invalid screen-file-name not UUID.json: <{}>\n#######\n#######".format(screen_cfg_data['screen-file-name']))
        return(0) ##### REVIEW/FIX/HACK/MAYBE EXCEPT???? EXIT???? ######
    else:
        screen_child_uuid = m.group(1)

    screen_meta_file = os.path.join(output_path, screen_child_uuid + "_meta.json")
    if debug:
            print("Screen child UUID is: <{}> and _meta path is: <{}>".format(screen_child_uuid, screen_meta_file))

    # now lets load the base_config
    with codecs.open(screen_config_file, "r", "utf-8") as BASE:
        new_screen_data = json.load(BASE, "utf-8")

    # now lets construct

    # SEENFURLS[tag][furl]
    seen_furls = dict()
    card_list_widgets = dict()  # key is a tag, value is the actual JSON to be added!

    # http://jira.quixeyplex.com/browse/SCREEN-678
    # 4/25/16 - eric@quixey.com
    # we will add the following fields:
    #
    # "interests" --> a STRING of a comma-separated list of interests pulled from the "interests" field of the config
    # "displayImage" --> A STRING path to an image
    #
    # "interests" and "ad-interests" are not the same thing
    # "ad-interests" refer to the "ad-interests" inside each CardListWidget

    interests_string = ",".join(screen_cfg_data['interests'])
    interests_string = interests_string.upper()
    new_screen_data['interests'] = interests_string

    if "display-image" in screen_cfg_data:
        new_screen_data['displayImage'] = screen_cfg_data['display-image']
    else:
        new_screen_data['displayImage'] = "None"

    for tab in screen_result_data.keys():
        seen_for_tab = set()
        seen_furls[tab] = seen_for_tab
        card_list_widgets[tab] = []
        # dvurls = []
        for result in screen_result_data[tab]:
            if 'furl' not in result:
                # ERROR - REQUIRED
                print(u"WARNING, missing a furl in result: <{}>".format(result).encode("utf-8"))
                continue
            furl = result['furl']
            if furl not in seen_furls[tab]:
                seen_furls[tab].add(furl)
                # lets add to the result structure for this tab!
                dvurl = dict()
                dvurl['dvUrl'] = furl
                if "url" in result and include_url:
                    dvurl['url'] = result['url']

                dvobj = {
                    "dvUrls": [dvurl]
                }
                card_list_widgets[tab].append(dvobj)

    if options.debug:
        print(u"Finished constructing card_list_widgets, now generating screen")

    # now lets add to the screen!
    max_dv_per_tab = screen_cfg_data.get('max_dv_per_tab', 10)

    # lets get the ad_interests
    ad_interests = ""
    # SCREEN-678

    if "ad-interests" in screen_cfg_data:
        ad_interests = ",".join(screen_cfg_data['ad-interests'])

    #print("Adding ad-interests of: {}".format(ad_interests))

    vl_counter = 0
    for tab in screen_cfg_data['tag_order']:
        if options.debug:
            print(u"Adding for tab: <{}>".format(tab).encode("utf-8"))
        if tab in card_list_widgets:
            vl_counter += 1

            vl = {
                "id" : "dvc_vertical_list_0" + unicode(vl_counter),
                    "idLabel" : tab,
                     "dataMap" : {
                        "label" : tab,
                         "index" : str(vl_counter - 1),
                         "ad_interests" : ad_interests
                      },
                    "funcUrls" : card_list_widgets[tab][0:max_dv_per_tab]
                }
            new_screen_data['cardListWidgets'].append(vl)

    # lets print/save
    if options.debug or options.test_run:
        print(u"Screen data is now:")

    json_out = json.dumps(new_screen_data, sort_keys=True, indent=4, ensure_ascii=False)

    if options.test_run:
        print(u"TEST RUN, NO FILES WRITTEN, SCREEN CONTENTS:\n{}".format(json_out).encode('utf-8'))
        return

    # lets save the file
    print(u"Saving output to: <{}>".format(screen_file_name).encode("utf-8"))
    with open(screen_file_name, "w") as SO:
        SO.write(u"{}".format(json_out).encode("utf-8"))

    if screen_cfg_data.get("gzip"):
        print(u"Building gzip file: <{}.gz>".format(screen_file_name).encode('utf-8'))

        with gzip.open(screen_file_name + ".gz", "w") as SOG:
            SOG.write(u"{}".format(json_out).encode('utf-8'))

    # we also need to make the _meta file
    # The _meta file has: https://docs.google.com/document/d/1I7j3lQGyYLuo6qJ6EKOoA4ZyVQzV04ir6bem8SVXK6o/edit#
    # screen-data -> interests : [<list of interests>]
    #             -> countries : [<two-letter-country-code>, ... ]
    screen_meta_data = dict()
    if "interests" in screen_cfg_data and ("countries" in screen_cfg_data or "country" in screen_cfg_data):

        interests = screen_cfg_data['interests']
        if "countries" in screen_cfg_data:
            countries = screen_cfg_data['countries']
        elif "country" in screen_cfg_data:
            countries = []
            countries.append(screen_cfg_data['country'])

        screen_data = {
            "interests" : interests,
            "countries" : countries
        }
        screen_meta_data['screen-data'] = screen_data

        json_out = json.dumps(screen_meta_data, sort_keys=True, indent=4, ensure_ascii=False)
        print(u"Saving screen meta-data file to: <{}>".format(screen_meta_file))

        with open(screen_meta_file, "w") as MF:
             MF.write(u"{}".format(json_out).encode('utf-8'))
    else:
        print("WARNING: Missing either 'interests' or 'countries' from screen config data for screen: <{}>".format(screen_file_name))

    return(screen_meta_file)