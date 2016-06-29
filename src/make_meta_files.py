from optparse import OptionParser
import os
import json
from collections import Counter
import pprint
import glob
import codecs
import csv
import re
from subprocess import Popen, PIPE
import subprocess
import sys

reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

__author__ = 'ericglover'

S3_CFG_PATH = os.environ.get('S3_CFG_PATH', "~/.s3cfg")
S3CMD_PATH = os.environ.get('S3CMD_PATH', "/usr/local/bin/s3cmd")

# This script will take an input CSV file and create (one at a time) SCREEN_meta.json file and copy to S3

# make_meta_files.py
#   -e env  [canary, prod, etc...]
#   -s <source_data_file.csv>  -- the file that specifies which screens we are making and with what data
#   [-w]  [default is ./meta_working_directory]
#   [-t]  Test mode - do not copy to S3



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

if __name__ == "__main__":

# make_meta_files.py
#   -e env  [canary, prod, etc...]
#   -s <source_data_file.csv>  -- the file that specifies which screens we are making and with what data
#   [-w]  [default is ./meta_working_directory]
#   [-t]  Test mode - do not copy to S3


    parser = OptionParser(
        description="Builds the files: interests.json, screensIndex.json, and furlsIndex.json\n"
                    "build_interests.py\n"
                    " -w <working-directory> (default ./working-dir/)\n"
                    " -e|--environment [Canary|prod|stage] (default is canary)\n"
                    " -s|--src_file <src_file> - the source file"
                    "[-d] enable debug - default is disabled\n"
                    "[-t] --test do not write to S3\n"
                        )

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="enable debug")

    parser.add_option("-t", "--test",
                      action="store_true", dest="test", default=False,
                      help="enable test")

    parser.add_option("-s", "--src_file", dest="src_file",
                      help="the csv file that lists the screen-ids,interests,countries, partner-id")

    parser.add_option("-w", "--working_directory", dest="working_directory", default="./meta-working-dir/",
                      help="the output path to store the temp files/sync from s3")

    parser.add_option("-e", "--environment", dest="environment", default="canary",
                      help="the environment to scan from")


    (options, args) = parser.parse_args()

    debug = options.debug
    if debug:
        print("Debug is enabled")

    # lets load the source file
    screen_meta_data = load_csv_file(options.src_file)
    for entry in screen_meta_data:
        screen_uuid = entry['screen_uuid']
        screen_json_id = entry['json_id']
        interests_string = entry['interests']
        interests = re.split("\s*\,\s*", interests_string)
        countries_string = entry['countries']
        countries = re.split("\s*,\s*", countries_string)
        partner_id = entry['partner_id']
        screen_name = entry['screen_name']

        # lets construct the _meta contents
        #{
        #"screen-data": {
        #"countries": [
        #    "in"
        #],
        #"interests": [
        #    "food and dining"
        #]
        #}
        #}
        screen_data = {
            "countries" : countries,
            "interests" : interests
        }

        meta_screen_contents = {
            "screen-data" : screen_data
        }

        # ensure the working directory exists
        assure_path_exists(options.working_directory)

        #m = re.search("^([0-9a-f\-]+)$", screen_json_id)
        #if not m:
        #    print("WARNING screen_json_id: <{}> is invalid, skipping.".format(screen_json_id))
        #    continue

        #screen_id = m.group(1)

        screen_meta_file_path = options.working_directory + screen_json_id + "_meta.json"
        json_out = json.dumps(meta_screen_contents, sort_keys=True, indent=4, ensure_ascii=False)

        s3_path = "s3://quixey-" + options.environment + "/screensConfig/screens/" + partner_id + "/" + screen_uuid + "/config/" + screen_json_id + "_meta.json"
        if options.test:
            print("Not saving file: {} with contents: ###\n{}\n###\n would copy to: <{}>".format(screen_meta_file_path, json_out, s3_path))
        else:
            # lets build the file in the working directory
            # lets save this file!
            print("Saving screens_index file: <{}>".format(screen_meta_file_path))
            with open(screen_meta_file_path, "w") as SM:
                SM.write(u"{}".format(json_out).encode('utf-8'))

            # now lets save the file to the proper S3 bucket
            command = S3CMD_PATH
            arguments = ["-c", S3_CFG_PATH, "put", "--force", screen_meta_file_path, s3_path ]

            r = execute_command(command, arguments)
            if not r:
                print("Failed to execute command - aborting with failure")
                sys.exit(1)