from optparse import OptionParser
import os
import json
import re

import sys
reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')



# This script is a library and command-line that can validate a JSON file as being good

#from: http://stackoverflow.com/questions/5508509/how-do-i-check-if-a-string-is-valid-json-in-python

def is_json(myjson):
  try:
    json_object = json.loads(myjson)
  except ValueError, e:
    return False
  return True

def our_errmsg(msg, doc, pos, end=None):
    json.last_error_position= json.decoder.linecol(doc, pos)
    return original_errmsg(msg, doc, pos, end)

if __name__ == "__main__":

    # global debug

    parser = OptionParser(
        description="Checks if a specified file is valid json - -f <file to check>"
    )

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="enable debug")

    parser.add_option("-f", dest="file_to_check", default="",
                      help="the file to check")

    (options, args) = parser.parse_args()

    if not options.file_to_check:
        print("ERROR: missing required parameter -f <file_to_check")
        exit(1)

    #print("Checking if: <{}> is valid JSON and can be loaded.".format(options.file_to_check))
    with open(options.file_to_check, "r") as FTC:
        json_data = FTC.read()

    result = is_json(json_data)
    if result:
        print("File: <{}> appears to be valid JSON.".format(options.file_to_check))
    else:
        print("File: <{}> appears to be NOT VALID JSON".format(options.file_to_check))
