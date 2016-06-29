from optparse import OptionParser
import os
import json
from collections import Counter
import pprint
import glob
import codecs
import csv
import re

import sys
reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

__author__ = 'ericglover'

# USAGE
# -n <node_id_file>
# -b <browse_paths_file>
# -s <screen_ranking_data_file>
# -t <screen_trending_data_file>
#
# [-d] enable debug
# -o <output_path> (default ./browse/)
# -T|--test-mode enable test mode do not write files only report/summarize

###############
# browse_builder overview
# This script will construct the browse files and "trending" (or promoted) files
#
# The structure is as follows:

# Top-level directory structure
# /browse/
#   ./trending/
#   ./browseList.json <- "old browse list" top 10 screens overall (for backwards compatibility)
#
#   ./NODE_ID/
#
#
#
# /browse/trending/
#    ./NODE_ID/trending.json <- The "promoted screens" for that NODE_ID
#    trending.son <- The "default promoted screens" - the top n overall from the "trending score"
#
# NOTE: Not all NODE_IDs will be defined under trending, if any are missing, then the "default trending" will be used.
#
#
# /browse/NODE_ID/browseList.json <- The browse list for the node NODE_ID
#
# browseList.json contents (excluding the top-level default old-style)
#
# "categoryUrl" -> The path of *this* browse list
# "screens" : array of screens to be listed at this level
# "children" : array of "nodes" that are linked to FROM this node, and for each a "screenUrl" array of up to 10 screens
#     to be shown in the "reduced tab". These screens will be the "top 10" screens based on their ScreenRankingData
#
# "parent" -> An array of "parent paths", only the first one will be used
#
# NOTE: all "paths" are of the form "/browse/NODE_ID1/NODE_ID2/NODE_ID3" - the "top" is "/browse/0"
#



# Data structures:
##################

# NODES --> Key is the ID, value is a dict with a "name" and "icon" and a "members" which is an Counter of members
#   (string screen_ids) -> score
# SCREEN_SCORES -> Counter: key is a screen_id, value is the screen_score from the ScreenRankingDataFile
# NODE_PATHS: key is a Node, value is the array of Nodes that are children of this node
#    i.e. if I have /0/1/2 and /0/2/3 and /0/4/5/2  then I have 0->[1,2,4], 1->[2], 2->[3], 3->[], 4->[5], 5->[2]
#
# TRENDING_SCORES = Dict, key is a Node, value is a Counter of key screen_id
# TRENDING_SCORES_TOP = Counter, key is a screen_id, score is the highest score for this screen in Trending
#       Highest of the score for any nodes this screen appears in
#
# Algorithm:
#
# 1: Load all data
# -- for NODE_PATHS take all "sub-paths" of the provided browse-paths
# ---- when loading the ScreenBowsePaths data - add the screen to each end-node of the path i.e. if a screen is in
#           /0/1 and /0/2/3 add the screen to both 1 and 3
# 2: Build the default browse (top NUM_DEFAULT_SCREENS) from the SCREEN_SCORES
# 3: Build the default trending from TRENDING_SCORES_TOP
# 4: Scan for coverage/loops
#   -- make a SET called "SEEN_PATHS" it is a string identifying an edge such as 0:1  which is
#        "node_id1:node_id2" meaning node 1 points to node 2
#   -- Scan from the "root node" - by default assumed to be 0 (ROOT_NODE_ID)
#   ---- Have a stackof "paths to explore", do a DFS - pop an item off the stack, get the next-nodes add those to
#        the stack. Each item added to the stack add parent->node to the set - if already in the set, you have a loop
# --- IF loop detected report "repeated path"
#
# 5: Build the per-node browse directories/files
#  --- for each node that has at least one child and or at least one screen
#     --- construct the browse screen: "all" for the current category "screens", up to MAX_SCREENS_PER_CHILD screens
#       for each child
#
# 6: Build the per-node trending directories/files
#    -- only for those entries keep the max MAX_TRENDING_SCREENS for each node

NUM_DEFAULT_SCREENS = 5000
MAX_SCREENS_PER_CHILD = 10
MAX_TRENDING_SCREENS = 5
ROOT_NODE = 0

def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]

def load_csv_file(file_name):
    # we load this file, assuming a Header
    # the output is an array of dicts, where the key is the column name
    results = []
    with codecs.open(file_name, 'rb', encoding='utf-8') as csvfile:
        csvreader = unicode_csv_reader(csvfile)
        header = []
        for row in csvreader:
            if len(header) == 0:
                header = row
            else:
                result_object = dict()
                for x in range(0,len(header)):
                    if len(row) > x:
                        result_object[header[x]] = row[x]
                    else:
                        result_object[header[x]] = ""
                results.append(result_object)

    return results

if __name__ == "__main__":

    # global debug

    parser = OptionParser(
        description="Generates the browse structure for screens 1.6.\n"
                    "Must specify each of the 4 required files.\n"
                    " -n <node_id_file>, -b <browse_paths_file>,\n"
                    " -s <screen_ranking_data_file>, -t <screen_trending_data_file>,\n"
                    " -p <partner_id>"
    )

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="enable debug")

    #parser.add_option("-p", "--partner_id", dest="partner_id",
    #                  help="the partner_id used for building the files")

    parser.add_option("-n", "--node_file", dest="node_file",
                      help="the node_id file to load")

    parser.add_option("-b", "--browse_paths_file", dest="browse_paths_file",
                      help="the browse_paths file to load")

    parser.add_option("-s", "--screen_ranking_file", dest="screen_ranking_file",
                      help="the screen_ranking data file to load")

    parser.add_option("-t", "--screen_trending_file", dest="screen_trending_file",
                      help="the screen_trending file to load")

    parser.add_option("-o", "--output_path", dest="output_path", default="./",
                      help="the output path to save all browse files")

    parser.add_option("-T", "--test_mode", dest="test_mode", action="store_true", default=False,
                      help="enable test mode - do not write any files")

    (options, args) = parser.parse_args()

    #if not options.partner_id:
    #    print("ERROR: missing required parameter partner_id")
    #    exit(1)

    #partner_id = options.partner_id

    debug = 0
    if options.debug:
        debug = 1

    if debug:
        print(u"Debug is enabled")

    # we want to load the files as per the directions above
    NODES = dict()
    SCREEN_SCORES = Counter()
    SCREEN_DATA = dict() # key is the screenid, value is the DisplayName (only for enabled)
    NODE_PATHS = dict()
    TRENDING_SCORES = dict()
    TRENDING_SCORES_TOP = Counter()
    PARENTS = dict()  # key is a node, value is an array of parents first add order
    ALL_OFFSPRING_NODES = dict() # key is a node, value is a set of *all* of the nodes that can be reached from this node
        # note - if a node is in its own offspring, we have a cycle
    ALL_OFFSPRING_SCREENS = dict() # key is a node, value is a Counter of all screens (with scores) that can be reached from this node

    TRENDING_ICONS = dict() # key is a screen_id, value is the last-seen "icon"

    # lets load the nodes file
    if debug:
        print("loading node_id file: <{}>".format(options.node_file))

    node_data = load_csv_file(options.node_file)
    print("loaded {} nodes from <{}>".format(len(node_data), options.node_file))

    if debug:
        for entry in node_data:
            print("{}".format(entry))

    # lets load the browse_paths file
    if debug:
        print("loading browse_paths file: <{}>".format(options.browse_paths_file))

    browse_path_data = load_csv_file(options.browse_paths_file)
    print("loaded {} nodes from <{}>".format(len(browse_path_data), options.browse_paths_file))

    if debug:
        for entry in browse_path_data:
            print("{}".format(entry))


    file = options.screen_ranking_file
    if debug:
        print("loading browse_paths file: <{}>".format(file))

    screen_ranking_data = load_csv_file(file)
    print("loaded {} nodes from <{}>".format(len(screen_ranking_data), file))

    if debug:
        for entry in screen_ranking_data:
            print("{}".format(entry))


    file = options.screen_trending_file
    if debug:
        print("loading browse_paths file: <{}>".format(file))

    screen_trending_data = load_csv_file(file)
    print("loaded {} nodes from <{}>".format(len(screen_trending_data), file))

    if debug:
        for entry in screen_trending_data:
            print("{}".format(entry))


    ### Lets scan the data and set up...

    # nodes
    for entry in node_data:
        node_id = entry['NodeId']
        display_name = entry['DisplayName']
        icon = entry['Icon']

        NODES[node_id] = entry
        NODES[node_id]['members'] = set()

    for entry in browse_path_data:
        if entry['Enabled'] == "TRUE":
            screen_id = entry['ScreenId']
            display_name = entry['DisplayName']
            browse_paths_string = entry['BrowsePaths']
            SCREEN_DATA[screen_id] = entry

            # lets scan the browse paths
            browse_paths = re.split("\s*,\s*", browse_paths_string)
            for browse_path in browse_paths:
                # lets get the array of node ids
                node_array = re.split("\s*/\s*", browse_path)
                if node_array[0] == "":
                    node_array.pop(0)
                #print("NA: <{}>".format(node_array))
                # the last node of each node_array is the "home"
                last_node = node_array[-1]
                if last_node in NODES:
                    NODES[last_node]['members'].add(screen_id)
                else:
                    print("WARNING: screen: <{}> <{}> refers to a node <{}> that is not in the NodeIds File".format(screen_id, display_name, last_node))

                # now we add all the paths
                for x in range(1,len(node_array)):
                    parent = node_array[x-1]
                    child = node_array[x]
                    if parent == "":
                        print("WARNING invalid parent for browse_paths entry: <{}>".format(entry))
                    if parent not in NODE_PATHS:
                        NODE_PATHS[parent] = set()

                    NODE_PATHS[parent].add(child)

                    if child not in PARENTS:
                        PARENTS[child] = []
                    if parent not in PARENTS[child]:
                        PARENTS[child].append(parent)

    for entry in screen_ranking_data:
        if debug:
            print("Adding screen score entry: <{}> -> <{}>".format(entry['ScreenId'], entry['Score']))
        SCREEN_SCORES[entry['ScreenId']] = int(entry['Score'])

    # trending
    for entry in screen_trending_data:
        node = entry['NodeId']
        screen_id = entry['Screen']
        score = entry['TrendScore']
        trending_icon = entry['TrendIcon']
        TRENDING_ICONS[screen_id] = trending_icon
        old_score = TRENDING_SCORES_TOP[screen_id]
        if score > old_score:
            TRENDING_SCORES_TOP[screen_id] = score

        if node not in TRENDING_SCORES:
            TRENDING_SCORES[node] = Counter()
        TRENDING_SCORES[node][screen_id] = score

    # lets build ALL_OFFSPRING_NODES, and then ALL_OFFSPRING_SCREENS
    # we must look for loops
    # we recurse for each node we calculate its offspring and we keep inserting
    # an inefficient algorithm is for each node, do a DFS but it works

    print("Building the ancestor graphs and checking for loops")
    for node in NODE_PATHS:
        ALL_OFFSPRING_NODES[node] = set()
        # lets do a DFS
        stack = list(NODE_PATHS[node])
        is_cycle = 0
        max_count = 10000
        count = 0

        while not is_cycle and len(stack) and count < max_count:
            count += 1
            next_node = stack.pop()

            if next_node == node:
                is_cycle = 1
            if count == max_count:
                is_cycle = 1  # not guaranteed, but very likely!

            ALL_OFFSPRING_NODES[node].add(next_node)
            if next_node in NODE_PATHS:
                stack.extend(list(NODE_PATHS[next_node]))

        if is_cycle:
            print("ERROR: Possible cycle found in paths at node: {}".format(node))
            exit(1)

    # build all offspring screens
    for node in NODES:
        ALL_OFFSPRING_SCREENS[node] = Counter()
        # add the current screens as well as all screens for all offspring
        for screen_id in NODES[node]['members']:
            ALL_OFFSPRING_SCREENS[node][screen_id] = SCREEN_SCORES[screen_id]

        if node in ALL_OFFSPRING_NODES:
            for offspring in ALL_OFFSPRING_NODES[node]:
                for screen_id in NODES[offspring]['members']:
                    ALL_OFFSPRING_SCREENS[node][screen_id] = SCREEN_SCORES[screen_id]

    ######
    if debug:
        print("All structures:")
        print("##### NODES ####")
        pprint.pprint(NODES)

        print("\n\n##### NODE_PATHS ####")
        pprint.pprint(NODE_PATHS)

        print("\n\n##### PARENTS ####")
        pprint.pprint(PARENTS)

        print("\n\n##### ALL_OFFSPRING_NODES ####")
        pprint.pprint(ALL_OFFSPRING_NODES)

        print("\n\n##### ALL_OFFSPRING_SCREENS ####")
        pprint.pprint(ALL_OFFSPRING_SCREENS)


        print("\n\n##### SCREEN_DATA ####")
        pprint.pprint(SCREEN_DATA)

        print("\n\n##### SCREEN_SCORES ####")
        pprint.pprint(SCREEN_SCORES)

        print("\n\n##### TRENDING_ICONS ####")
        pprint.pprint(TRENDING_ICONS)

        print("\n\n##### TRENDING_SCORES ####")
        pprint.pprint(TRENDING_SCORES)

        print("\n\n##### TRENDING_SCORES_TOP ####")
        pprint.pprint(TRENDING_SCORES_TOP)

    #### Done loading, now lets construct the files
    if debug:
        print("\n##### Build master browse screen ####")
    master_browse = dict()
    screens = []
    top_screens = SCREEN_SCORES.most_common(NUM_DEFAULT_SCREENS)

    if debug:
        print("master browse - top_screens is:<{}>".format(top_screens))
    for screen_id, score in top_screens:
        if screen_id not in SCREEN_DATA:
            continue

        obj = {
            "screenUrl" : "/screen/" + screen_id,
            "displayName" : SCREEN_DATA[screen_id]['DisplayName'],
            "displayIcon" : SCREEN_DATA[screen_id]['BrowseIcon'],
            "ownerId" : SCREEN_DATA[screen_id]['OwnerId']
        }
        screens.append(obj)
        if debug:
            print("Adding browse screen: <{}>".format(screen_id))
    master_browse['screens'] = screens

    master_browse_file = options.output_path + "browseList.json"
    json_out = json.dumps(master_browse, sort_keys=True, indent=4, ensure_ascii=False)
    if options.test_mode:
        print("TEST_MODE: file: <{}> ".format(master_browse_file))
        print(json_out)
    else:
#        if debug:
        print("Building file: <{}>".format(master_browse_file))
        with open(master_browse_file, "w") as MBO:
            MBO.write(u"{}".format(json_out).encode('utf-8'))

    # master trending file
    master_trending = dict()
    screens = []
    for screen_id, score in TRENDING_SCORES_TOP.most_common(MAX_TRENDING_SCREENS):
        if screen_id in SCREEN_DATA:
            # we want the TRENDING ICON, not the regular screen_data icon!

            display_icon = "None"
            if screen_id in SCREEN_DATA:
                display_icon = SCREEN_DATA[screen_id]['BrowseIcon']
            obj = {
                "screenUrl" : "/screen/" + screen_id,
                "displayName" : SCREEN_DATA[screen_id]['DisplayName'],
                "displayImage" : TRENDING_ICONS[screen_id],
                "displayIcon" : display_icon ,
                "ownerId" : SCREEN_DATA[screen_id]['OwnerId']
            }
            screens.append(obj)

    master_trending['trending'] = screens

    master_trending_file = options.output_path + "trending/trending.json"
    json_out = json.dumps(master_trending, sort_keys=True, indent=4, ensure_ascii=False)
    if options.test_mode:
        print("TEST_MODE: file: <{}> ".format(master_trending))
        print(json_out)
    else:
#        if debug:
        # check for the directory trending
        trend_dir = options.output_path + "trending/"
        if not os.path.isdir(trend_dir):
            print("Making directory: <{}>".format(trend_dir))
            os.makedirs(options.output_path + "trending/")
        print("Building file: <{}>".format(master_trending_file))
        with open(master_trending_file, "w") as MTO:
            MTO.write(u"{}".format(json_out).encode('utf-8'))

    print("Building the individual browse files")
    # now lets build the individual browse files
    for node in NODES:
        # we confirm we have at least one screen or one child
        num_children = 0
        children = []
        member_screens = NODES[node]['members']
        num_screens = len(member_screens)
        children_ids = []
        if node in NODE_PATHS:
            children_ids = NODE_PATHS[node]
            num_children = len(children_ids)

        if num_screens + num_children == 0:
            print("WARNING: Node <{}> : <{}> has no children or screens".format(node, NODES[node]['DisplayName']))
            continue

        #if debug:
        print("Building for node: <{}> : <{}>, with children: <{}>, and screens: <{}>".format(node, NODES[node]['DisplayName'], children_ids, member_screens))

        # now lets build the browsefile
        browse_file_directory = options.output_path + str(node) + "/"
        browse_file_path = browse_file_directory + "browseList.json"

        # set up the contents
        browse_file_data = dict()
        browse_file_data['categoryUrl'] = "/browse/" + str(node)
        screens = []
        children = []
        parents = []
        if node in PARENTS:
            for parent in PARENTS[node]:
                parents.append("/browse/" + str(parent))

        browse_file_data['parent'] = parents

        # lets keep in order by score
        tmp_screens = Counter()
        for screen_id in member_screens:
            tmp_screens[screen_id] = SCREEN_SCORES[screen_id]

        #print("TMP_SCREENS: <{}>".format(tmp_screens.most_common()))
        # we assume sort by score...
        tmp_seen_screens = set()
        for screen_id, score in tmp_screens.most_common():
            tmp_seen_screens.add(screen_id)
            obj = {
                "screenUrl" : "/screen/" + screen_id,
                "displayName" : SCREEN_DATA[screen_id]['DisplayName'],
                "displayIcon" : SCREEN_DATA[screen_id]['BrowseIcon'],
                "ownerId" : SCREEN_DATA[screen_id]['OwnerId']
            }
            screens.append(obj)

        if len(screens) < MAX_SCREENS_PER_CHILD and str(node) != str(ROOT_NODE):
            num_extra_screens = MAX_SCREENS_PER_CHILD - len(screens)
            for screen_id, score in ALL_OFFSPRING_SCREENS[node].most_common(num_extra_screens):
                if screen_id not in tmp_seen_screens:
                    tmp_seen_screens.add(screen_id)
                    obj = {
                        "screenUrl" : "/screen/" + screen_id,
                        "displayName" : SCREEN_DATA[screen_id]['DisplayName'],
                        "displayIcon" : SCREEN_DATA[screen_id]['BrowseIcon'],
                        "ownerId" : SCREEN_DATA[screen_id]['OwnerId']
                    }
                    screens.append(obj)

        # now for the children
        for child in children_ids:
            #print("Checking child: <{}>".format(child))

            tmp_screens = Counter()
            for screen_id in NODES[child]['members']:
                tmp_screens[screen_id] = SCREEN_SCORES[screen_id]

            #print("TMP_SCREENS: <{}>".format(tmp_screens.most_common()))
            #for screen, score in tmp_screens.most_common():
            children_screens = []

            for screen_id, score in ALL_OFFSPRING_SCREENS[child].most_common(MAX_SCREENS_PER_CHILD):
                children_screens.append("/screen/" + screen_id)
            if str(node) == str(ROOT_NODE):
                children_screens = []

            obj = {
                "categoryUrl" : "/browse/" + str(child),
                "displayName" : NODES[child]['DisplayName'],
                "displayIcon" : NODES[child]['Icon'],
                "screenUrl" : children_screens
            }
            children.append(obj)


        browse_file_data['screens'] = screens
        browse_file_data['children'] = children


        json_out = json.dumps(browse_file_data, sort_keys=True, indent=4, ensure_ascii=False)
        if options.test_mode:
            print("TEST_MODE: file: <{}> ".format(browse_file_path))
            print(json_out)
        else:
    #        if debug:
    # check for the directory trending

            if not os.path.isdir(browse_file_directory):
                print("Making directory: <{}>".format(browse_file_directory))
                os.makedirs(browse_file_directory)
            print("Building file: <{}>".format(browse_file_path))
            with open(browse_file_path, "w") as BFP:
                BFP.write(u"{}".format(json_out).encode('utf-8'))

