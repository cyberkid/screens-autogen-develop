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

# This script will take a screen (all the required files) from one env and copy it to another
# copy_s3_screen.py -p <partner_id> -s <source_env> -d <dest_env> -c <screen_cfg>
# Files copied:
#
# ScreenControlData.json
# Child_screen_UUID.json
# Child_screen_UUID.json.gz
# Child_screen_UUID_meta.json

S3_CFG_PATH = os.environ.get('S3_CFG_PATH', "~/.s3cfg")
S3CMD_PATH = os.environ.get('S3CMD_PATH', "/usr/local/bin/s3cmd")


def execute_command(command, arguments, is_test):

    display_command = command + " " + " ".join(arguments)
    if is_test:
        print("TEST MODE - not executing")

    print "Executing command: {}".format(display_command)

    if is_test:
        return 1

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

if __name__ == "__main__":

    # global debug

    parser = OptionParser(
        description="copy_s3_screen.py -s <source_env> -d <dest_env> -c <screen_cfg> [-w <working-directory] [-t]"
                        )

#    parser.add_option("-p", "--partner_id", dest="partner_id",
#                      help="the screen's partner-id")

    parser.add_option("-t", "--test-mode",
                      action="store_true", dest="test_mode", default=False,
                      help="test-mode do not copy files")

    parser.add_option("-s", "--source_env", dest="source_env",
                      help="the source_env (stage, canary, etc...)")

    parser.add_option("-w", "--working_dir", dest="working_dir", default="/tmp",
                      help="the working_directory default '/tmp/")

    parser.add_option("-d", "--dest_env", dest="dest_env",
                      help="the dest_environment")

    parser.add_option("-c", "--screen_cfg", dest="screen_cfg",
                      help="autogen screen.json config file")

    (options, args) = parser.parse_args()

    # The code will simply copy the "source" to the "destination" for each of the four files...

    # first we open the config file and get the screen-id, partner id, child-screen-id
    with open(options.screen_cfg, "r") as SCFG:
        screen_file_data = json.load(SCFG, "utf-8")

    screen_id = screen_file_data["screen-uuid"]
    screen_child_file = screen_file_data["screen-file-name"]
    partner_id = screen_file_data["partnerid"]

    test_mode = options.test_mode

    # lets prepare the source and dests
    source_base_path = "s3://quixey-" + options.source_env + "/screensConfig/screens/" + partner_id + "/" + screen_id + "/config/"
    dest_base_path = "s3://quixey-" + options.dest_env + "/screensConfig/screens/" + partner_id + "/" + screen_id + "/config/"

    # now prepare the file names
    m = re.search("^([a-z0-9\-]+)\.json$", screen_child_file)
    if not m:
        print("Invalid screen-file-name <{}> from config <{}>".format(screen_child_file, options.screen_cfg))
        sys.exit(1)

    child_uuid = m.group(1)

    control_file = "ScreenControlData.json"
    screen_gz_file = screen_child_file + ".gz"
    screen_meta_file = child_uuid + "_meta.json"

    # lets copy the control_file
    command = S3CMD_PATH

    for file_to_copy in [control_file, screen_child_file, screen_gz_file, screen_meta_file]:

        arguments = ["-c", S3_CFG_PATH, "cp", "--force", source_base_path + file_to_copy, dest_base_path ]

        r = execute_command(command, arguments, test_mode)
        if not r:
            print("Failed to execute command - aborting with failure")
            sys.exit(1)

