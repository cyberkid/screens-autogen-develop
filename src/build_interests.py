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
from subprocess import Popen, PIPE
import subprocess

reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

__author__ = 'ericglover'

S3_CFG_PATH = os.environ.get('S3_CFG_PATH', "~/.s3cfg")
S3CMD_PATH = os.environ.get('S3CMD_PATH', "/usr/local/bin/s3cmd")
max_screens_per_index = 50
max_furls_per_index = 50

############
# build_interests.py -f <furls-list-file> -a <active-screens-file> -s <screen-scores-file> -w <working-directory>
# optional [-d], -e [canary|prod|stage] (default is canary - environment)

# Process:
# Input: the 3 files: the furls-list-file, active-screens-file, screen-scores-file
# Output: the OUT_DIR/Country_code/interests.json
#         OUT_DIR/Country_code/screensIndex.json
#         OUT_DIR/Country_code/furlsIndex.json

# Algorithm:
# create the directory: working_directory/screens_data/env/<ALL_SCREEN_DATA>
# do an s3cmd to sync the contents to the entire s3 structure -- this is easier/faster than trying to pull each
#     individual screen file
#
# Now we scan:
# Scan 1: Interests for screens: scan the specified <screen_UUID>_meta.json files that are on the list
# --- scan all files that are X_meta.json, see if X is on the list, if so "update" the interests data
#
# Scan 2: The furls-file - this is one file
# INTEREST_TO_FURL[interest]-> Counter(FURL) -> score
# FURLS_TO_INTERESTS[furl] = set of interests
# FURL_SCORES = Counter(furl) -> score

# Scan 3: The scores file - put into a structure: <parent_screen_UUID> ---> Score

# Build the output

def execute_command(command, arguments):

    display_command = command + " " + " ".join(arguments)
    print "Executing command: {}".format(display_command)

    try:
        command_plus_args = [command]
        command_plus_args.extend(arguments)
        p = Popen(command_plus_args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate(b"input data that is passed to subprocess' stdin")
        rc = p.returncode

        print output, err
        if rc is not 0:
            print(u"Failure")
            return 0
        else:
            print(u"Success")
            return 1
    except subprocess.CalledProcessError as e:
        print(u"Exception occured: {}".format(e.message).encode("utf-8"))
        print(u"Failed executing command: {}".format(display_command).encode("utf-8"))

        return 0

def assure_path_exists(path):
        dir = os.path.dirname(path)
        if not os.path.exists(dir):
                os.makedirs(dir)

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
        description="Builds the files: interests.json, screensIndex.json, and furlsIndex.json\n"
                    "build_interests.py -f <furls-list-file> -a <active-screens-file> -s <screen-scores-file>\n"
                    " -w <working-directory> (default ./working-dir/)\n"
                    " -o <output-directory> (default ./search/)\n"
                    " -e|--environment [Canary|prod|stage] (default is canary)\n"
                    "[-d] enable debug - default is disabled\n"
                    "[-D] --deploy deploy the built files automatically\n"
                        )

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="enable debug")

    parser.add_option("-f", "--furls_file", dest="furls_file",
                      help="the file that lists the furls,interests,score")

    parser.add_option("-a", "--active_screens_file", dest="active_screens_file",
                      help="the file that lists the active screens form: <parent_UUID>/<individual_screen_UUID>")

    parser.add_option("-s", "--screen_scores_file", dest="screen_scores_file",
                      help="the file that lists the furls,interests,score")

    parser.add_option("-o", "--output_path", dest="output_path", default="./search/",
                      help="the output path to save all browse files")

    parser.add_option("-w", "--working_directory", dest="working_directory", default="./working-dir/",
                      help="the output path to store the temp files/sync from s3")

    parser.add_option("-e", "--environment", dest="environment", default="canary",
                      help="the environment to scan from")


    (options, args) = parser.parse_args()

    debug = options.debug
    if debug:
        print("Debug is enabled")

    full_working_directory = options.working_directory + options.environment + "/"
    # make sure the working directory exists
    assure_path_exists(options.working_directory)
    assure_path_exists(full_working_directory) # this has the environment added

    if debug:
        print("Going to use the working directory of: <{}>".format(full_working_directory))

    # lets set up the s3-cmd to do the fetch
    # time s3cmd sync s3://quixey-canary/screensConfig/screens/ ./
    command = S3CMD_PATH
    arguments = ["-c", S3_CFG_PATH, "sync", "--force", "s3://quixey-" + options.environment + "/screensConfig/screens/", full_working_directory ]

    r = execute_command(command, arguments)
    if not r:
        print("Failed to execute command - aborting with failure")
        sys.exit(1)

    ###### SETUP THE DATA STRUCTURES ######
    # we have furls per-country, screens per-country (note - anything could be valid in more than one country)
    # we map interests to furls/screens (and should do this per-country)
    # we need to utilize the scores to select items to then select interests and then rank the items...

    # FURLS
    furls_to_interests = dict() # A dict of furls which points to a set of interests
    interests_to_furls = dict() # key is a country to a dict of an interest, which points to a Counter where the key is a furl, and the count is the score
            # interests_to_furls[country][interest][furl] -> score
    furl_scores = dict() # key is a country, then value is a Counter() # key is a furl, value is it's score
    screen_scores = dict() # key is a country, then value is a Counter() # key is a parent-screen-id, value is the score of that screen -- note, we only store active
    interests_to_screens = dict() # Key is a country, value is Dict of interests which point to a Counter of screenIDs interests_to_screens[country][interest][screen_UUID] -> ScreenScore
    screens_to_interests = dict() # Key is a ScreenUUID -> set of interests
    all_countries = [] # a list of unique countries in some order
    active_screens = set() # set of active screen UUIDs
    all_screen_scores = Counter() # key is a screen-id, value is the score
    #######
    # lets load the active-screens
    active_screens_data = load_csv_file(options.active_screens_file)
    for entry in active_screens_data:
        screen_id = entry['screenid']
        active_screens.add(screen_id)

    # lets load the furls
    furls_data = load_csv_file(options.furls_file)
    for entry in furls_data:
        furl = entry['furl']
        score = int(entry['score'])
        interest_array_tmp = re.split("\s*,\s*", entry['interests'])
        furl_countries = re.split("\s*,\s*", entry['countries'])
        interest_array = []
        for item in interest_array_tmp:
            interest_array.append(item.upper())

        furls_to_interests[furl] = set(interest_array)

        for country in furl_countries:
            if country not in all_countries:
                all_countries.append(country)

            if country not in furl_scores:
                furl_scores[country] = Counter()

            furl_scores[country][furl] = score

            for interest in interest_array:
                if country not in interests_to_furls:
                    interests_to_furls[country] = dict()

                if interest not in interests_to_furls[country]:
                    interests_to_furls[country][interest] = Counter()

                interests_to_furls[country][interest][furl] = score

    # lets load the screen scores
    screen_scores_data = load_csv_file(options.screen_scores_file)
    for entry in screen_scores_data:
        screen_id = entry['ScreenId']
        score = int(entry['Score'])

        if screen_id in active_screens:
            all_screen_scores[screen_id] = score # we can't update the other data until we finish scanning all the files

    # lets scan the local files
    print("Checking files in S3 for matched screens with _meta (interest and country data)")
    for cur, _dirs, files in os.walk(full_working_directory):
        # we look for "cur" = XXXX/UUID/config
        # then we look for files UUID_meta.json
        m = re.search("\/([0-9a-f\-]+)\/config$", cur)
        if m:
            screen_id = m.group(1)
            # now look for a meta
            matched = 0
            files_to_check = []
            for file in files:
                m = re.search("_meta.json$", file)
                if m:
                    matched = 1
                    files_to_check.append(file)
            if matched != "":
                # lets check if hte screen is on the active screens list
                if screen_id in active_screens:
                    # we can load the file!
                    # lets preserve the score
                    interests = set()
                    countries = set()
                    if debug:
                        print("Matched active parent screen: <{}> with a _meta in files: <{}>".format(screen_id, files_to_check))

                    for file in files_to_check:
                        full_path = cur + "/" + file
                        with open(full_path, "r") as IF:
                            meta_file_data = json.load(IF, "utf-8")
                            # we want to get the countries and the interests
                            if "country" in meta_file_data['screen-data']:
                                country = meta_file_data['screen-data']['country']
                                countries.add(country)
                            elif "countries" in meta_file_data['screen-data']:
                                countries |= set(meta_file_data['screen-data']['countries'])
                            else:
                                print("WARNNING no 'countries' in <{}> child of <{}>".format(full_path, screen_id))

                            if 'interests' in meta_file_data['screen-data']:
                                new_interests_tmp = meta_file_data['screen-data']['interests']
                                new_interests = []
                                for item in new_interests_tmp:
                                    new_interests.append(item.upper())
                                if len(new_interests):
                                    interests |= set(new_interests)
                            else:
                                print("WARNNING no 'interests' in <{}> child of <{}>".format(full_path, screen_id))

                    if debug:
                        print("Got countries: <{}> and interests <{}> from file: <{}> and parent screen: <{}>".format(countries, interests, file, screen_id))
                    screen_score = all_screen_scores[screen_id]
                    if len(countries) > 0:
                        for country in countries:

                            if country not in all_countries:
                                all_countries.append(country)

                            if country not in screen_scores:
                                screen_scores[country] = Counter()
                            screen_scores[country][screen_id] = all_screen_scores[screen_id]

                            for interest in interests:
                                screens_to_interests[screen_id] = interests
                                if country not in interests_to_screens:
                                    interests_to_screens[country] = dict()

                                if interest not in interests_to_screens[country]:
                                    interests_to_screens[country][interest] = Counter()

                                interests_to_screens[country][interest][screen_id] = screen_score

                            # interests_to_screens[country][interest][screen_UUID] -> ScreenScore
    # lets print the data if debug
    if debug:
        print("######### ALL DATA BEFORE BUILDING #########")
        print("\n### furls_to_interests ###")
        pprint.pprint(furls_to_interests)

        print("\n### interests_to_furls ###")
        pprint.pprint(interests_to_furls)

        print("\n### furl_scores ###")
        pprint.pprint(furl_scores)

        print("\n### screens_to_interests ###")
        pprint.pprint(screens_to_interests)

        print("\n### interests_to_screens ###")
        pprint.pprint(interests_to_screens)

        print("\n### screen_scores ###")
        pprint.pprint(screen_scores)

        print("\n### countries ###")
        pprint.pprint(all_countries)


    #   IF a screen is not active, then we do not include it, if active and no-score we give it a -1
    # now that we have everything.....
    # we want to load the files and do some scanning...

    # lets make sure the output directory base exists
    if not os.path.isdir(options.output_path):
            print("Making directory: <{}>".format(options.output_path))
            os.makedirs(options.output_path)

    for country in all_countries:
        # we have three files to produce for each country:
        # interests.json
        # screensIndex.json
        # furlsIndex.json

        output_directory = options.output_path + country + "/"
        # lets make sure the directory per country exists
        if not os.path.isdir(output_directory):
            print("Making directory: <{}>".format(output_directory))
            os.makedirs(output_directory)

        interests_file = output_directory + "interests.json"
        screens_index_file = output_directory + "screensIndex.json"
        furls_index_file = output_directory + "furlsIndex.json"

        # lets select interests
        # algorithm - we pick the best not yet covered screen (highest score) for a given country
        # we then choose an interest - pick one with the fewest screens (or first in sort order)
        # we add the screen to the selected_screens and the interest to the output_interests
        # then we select the next best (uncovered screen) until either all screens are included or skipped
        # we skip a screen that has no interests - and if an interests covers more than one screen we ensure all
        # covered screens are marked as selected

        # now lets construct the output
        selected_screens = set() # the set of screen-ids that have had at least one interest already selected
        selected_screen_interests = [] # the ordered list of screen-interests that have been selected
        selected_furls = set() # the set of furls that have had at least one interest already selected
        selected_furl_interests = [] # the set of furl-interests that have been selected

        if country not in screen_scores:
            screen_scores[country] = Counter()

        for screen, screen_score in screen_scores[country].most_common():
            if screen in selected_screens:
                # we need to make a blank screens file
                continue

            # find the interests
            best_interest = ""
            interest_score = 99999
            if screen in screens_to_interests:
                for interest in screens_to_interests[screen]:
                    new_interest_score = len(interests_to_screens[country][interest])
                    if not best_interest:
                        best_interest = interest
                        # the interest score is the number of screens that match that interest - lower is better
                        interest_score = new_interest_score
                    elif new_interest_score < interest_score:
                        best_interest = interest
                        interest_score = new_interest_score

                if debug:
                    print("# Selecting interest: {}, screen: {}, screen_score: {}".format(best_interest, screen, all_screen_scores[screen]))

                selected_screen_interests.append(best_interest)
                for sel_screen in interests_to_screens[country][best_interest]:
                    selected_screens.add(sel_screen)

        print("Selected interests in order for country: {}: <{}>".format(country, selected_screen_interests))
        interests_output = dict()
        interests_output['interests'] = selected_screen_interests

        ######## ScreensIndex.json
        # for each interest list the screens!

        screens_index = dict()
        # key is the interest
        # value is the array of screen_paths  /screen/screen_id
        for interest in selected_screen_interests:
            screens_index[interest] = []
            for screen, score in interests_to_screens[country][interest].most_common(max_screens_per_index):
                screens_index[interest].append("/screen/" + screen)

        screens_index_output = {
            "screensIndex" : screens_index
        }

        json_out = json.dumps(screens_index_output, sort_keys=True, indent=4, ensure_ascii=False)
        # lets save this file!
        print("Saving screens_index file: <{}>".format(screens_index_file))
        with open(screens_index_file, "w") as SI:
            SI.write(u"{}".format(json_out).encode('utf-8'))

        ###### Now lets do FURLS index
        # The same as for screens, but the MORE Furls the better instead of the fewer...
        if country not in furl_scores:
            furl_scores[country] = Counter()

        for furl, furl_score in furl_scores[country].most_common():
            if furl in selected_furls:
                continue

            # find the interests
            best_interest = ""
            interest_score = 0
            if furl in furls_to_interests:
                for interest in furls_to_interests[furl]:
                    new_interest_score = len(interests_to_furls[country][interest])
                    if not best_interest:
                        best_interest = interest
                        # the interest score is the number of screens that match that interest - lower is better
                        interest_score = new_interest_score
                    elif new_interest_score > interest_score:
                        best_interest = interest
                        interest_score = new_interest_score

                if debug:
                    print("# Selecting interest: {}, furl: {}, furl_score: {}".format(best_interest, furl, furl_scores[country][furl]))

                selected_furl_interests.append(best_interest)
                for sel_furl in interests_to_furls[country][best_interest]:
                    selected_furls.add(sel_furl)
        print("Selected FURL - interests in order for country: {}: <{}>".format(country, selected_furl_interests))
        interests_output['interests'].extend(selected_furl_interests)
        json_out = json.dumps(interests_output, sort_keys=True, indent=4, ensure_ascii=False)
        # lets save this file!
        print("Saving interests file: <{}>".format(interests_file))
        with open(interests_file, "w") as IF:
            IF.write(u"{}".format(json_out).encode('utf-8'))


        ######## FurlsIndex.json
        # for each furls_interest list the screens!

        furls_index = dict()
        # key is the interest
        # value is the array of screen_paths  /screen/screen_id
        for interest in selected_furl_interests:
            furls_index[interest] = []
            for furl, score in interests_to_furls[country][interest].most_common(max_furls_per_index):
                furls_index[interest].append(furl)

        furls_index_output = {
            "furlsIndex" : furls_index
        }

        json_out = json.dumps(furls_index_output, sort_keys=True, indent=4, ensure_ascii=False)
        # lets save this file!
        print("Saving furls_index file: <{}>".format(screens_index_file))
        with open(furls_index_file, "w") as SI:
            SI.write(u"{}".format(json_out).encode('utf-8'))