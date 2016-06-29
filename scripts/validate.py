import os
import json
from glob import glob
import boto
from optparse import OptionParser


# RUNNING DIRECTIONS: Run this from autogen directory

# See comments for what checks are carried out

def validate_local_screen_configs():
    screen_to_template_map = {}
    template_screens_have_duplicated_ids = False
    print "ID : Parent-UUID MAP"
    for template_screen_config_file_name in glob(os.path.join("config", "*-screen-cfg.json")):
        with open(template_screen_config_file_name) as template_screen_config_file:
            template_screen_config_json = json.load(template_screen_config_file)
            screen_id = template_screen_config_json['id']
            parent_uuid = template_screen_config_json['screenId']

            if screen_id in screen_to_template_map:
                print(u"{} and {} use the same ID".format(
                    template_screen_config_file_name,
                    screen_to_template_map[screen_id]['template_screen_config_file_name']).encode("utf-8"))
                template_screens_have_duplicated_ids = True

            screen_to_template_map[screen_id] = {
                'parent_uuid': parent_uuid,
                'template_screen_config_file_name': template_screen_config_file_name
            }

            print(u"{} : {}".format(screen_id, parent_uuid).encode("utf-8"))
    print "\n"
    if template_screens_have_duplicated_ids:
        print(u"Some template screens use the same screens")
    else:
        print(u"All template screens use distinct screens")
    print "\n"
    print(u"Checking whether the -screen-cfg.json and -screen.json have the right mappings")
    covered_template_screen_configs = set()
    for screen_config_file_name in glob(os.path.join("config", "*-screen.json")):
        with open(screen_config_file_name) as screen_config_file:
            screen_config_json = json.load(screen_config_file)

            screen_file_name = screen_config_json['screen-file-name']
            screen_id, _ext = os.path.splitext(screen_file_name)

            covered_template_screen_configs.add(screen_id)

            if os.path.abspath(screen_to_template_map[screen_id]['template_screen_config_file_name']) != \
                    os.path.abspath(screen_config_json['screen-config-base']):

                print "The -screen-cfg file: {} doesn't match -screen file:{}'s -screen-cfg file: {} but they both " \
                      "use the same id: {}".format(
                    screen_to_template_map[screen_id]['template_screen_config_file_name'],
                    screen_config_file_name,
                    screen_config_json['screen-config-base'],
                    screen_id
                )
            else:
                print(u"GOOD: {} : {}".format(
                    screen_config_file_name,
                    screen_to_template_map[screen_id]['template_screen_config_file_name']).encode("utf-8"))
    print "\n"
    non_covered_screens = set(screen_to_template_map.keys()) - covered_template_screen_configs
    if non_covered_screens:
        print "Some template screen config files exist that don't have matching screen config files: {}".format(
            non_covered_screens
        )
    else:
        print "All template screen config files have matching screen config files."


def get_directory_name(path):
    folder_name = os.path.basename(path)
    if not folder_name:
        path = os.path.dirname(path)
        folder_name = os.path.basename(path)
    return folder_name


def validate_config_folder(bucket, config_folder):
    entries = bucket.list(config_folder.name, "/")
    files = []
    for entry in entries:
        if not entry.name.endswith("/"):
            files.append(entry)

    screen_control_data_entry = None
    screen_json_entries = []
    screen_json_gz_entries = []
    for file_entry in files:
        file_entry_name = get_directory_name(file_entry.name)
        if file_entry_name == "ScreenControlData.json":
            screen_control_data_entry = file_entry
        else:
            file_entry_prefix, extension = os.path.splitext(file_entry_name)
            if extension == ".json":
                screen_json_entries.append((file_entry, file_entry_name))
            elif extension == ".gz":
                screen_json_gz_entries.append((file_entry, file_entry_prefix))
            else:
                pass

    print(u"\n")
    print "Validating {}".format(config_folder.name)

    test_failed = False
    if not screen_control_data_entry:
        print "{} doesn't have ScreenControlData.json file".format(config_folder.name)
        test_failed = True

    if not screen_json_entries:
        print(u"{} doesn't have .json files".format(config_folder.name).encode("utf-8"))
        test_failed = True

    if not screen_json_gz_entries:
        print(u"{} doesn't have .json.gz files".format(config_folder.name).encode("utf-8"))
        test_failed = True

    if test_failed:
        return False

    if len(screen_json_entries) != 1:
        print(u"There are more than one json files in {}".format(config_folder.name).encode("utf-8"))
        test_failed = True

    if len(screen_json_gz_entries) != 1:
        print(u"There are more than one json.gz files in {}".format(config_folder.name).encode("utf-8"))
        test_failed = True

    if test_failed:
        return False

    if screen_json_gz_entries[0][1] != screen_json_entries[0][1]:
        print(u"The json file and the json.gz files have different GUIDs: {}, {}".format(
            screen_json_entries[0][1],
            screen_json_gz_entries[0][1]).encode("utf-8"))
        return False

    screen_json_entry = screen_json_entries[0][0]
    screen_json_gz_entry = screen_json_gz_entries[0][0]

    screen_json = json.loads(screen_json_entry.get_contents_as_string())
    screen_control_data_entry_json = json.loads(screen_control_data_entry.get_contents_as_string())

    screen_id_a = screen_json.get('id')
    parent_uuid_a = screen_json.get('screenId')

    screen_id_b = screen_control_data_entry_json['criteria'][0]['defaultPath']
    parent_uuid_b = screen_control_data_entry_json['id']

    if parent_uuid_a != parent_uuid_b:
        print(u"The screen json and screen control data json files have different values "
              u"for parent UUID: {}, {}".format(
            parent_uuid_a, parent_uuid_b).encode("utf-8"))
        return False

    if not parent_uuid_a.startswith("/screen/"):
        print(u"The parent UUID should start with /screen/: {}".format(parent_uuid_a).encode("utf-8"))
        return False

    if len(parent_uuid_a) != len("/screen/") + 36:
        print(u"The parent UUID is not of the format /screen/<GUID>: {}".format(parent_uuid_a).encode("utf-8"))
        return False

    if len(screen_id_a) != 36:
        print(u"The screen ID in screen json is not a GUID: {}".format(screen_id_a).encode("utf-8"))
        return False

    if screen_id_b != "config/{}.json".format(screen_id_a):
        print(u"The screen ID in screen control data json should be of the format config/<GUID>.json: {}".format(
            screen_id_b).encode("utf-8"))
        return False

    print(u"... LOOKS GOOD")

    return True

def validate_parent_folder(bucket, parent):
    entries = bucket.list(parent.name, "/")
    config_entry = None
    for entry in entries:
        entry_name = get_directory_name(entry.name)
        if entry_name == "config":
            config_entry = entry
            break

    if not config_entry:
        print(u"{} doesn't have config folder".format(parent.name).encode("utf-8"))
        return False

    return validate_config_folder(bucket, config_entry)


def validate_browse_list():
    print "\n"
    print "Validating browseList.json"
    browse_list_entry = bucket.get_key("screensConfig/screens/browse/browseList.json")
    browse_list_has_error = False
    if not browse_list_entry:
        print "ERROR: browseList.json doesn't exit!"
        browse_list_has_error = True

    browse_list_json = {}
    if not browse_list_has_error:
        browse_list_json = json.loads(browse_list_entry.get_contents_as_string())
        if not isinstance(browse_list_json, dict):
            print(u"browseList.json is not a valid json file")
            browse_list_has_error = True

    screens = []
    if not browse_list_has_error:
        screens = browse_list_json.get("screens")
        if not isinstance(screens, list):
            print(u"browseList.json / screens should be a list")
            browse_list_has_error = True

    if not browse_list_has_error and not screens:
        print(u"There are no screens in browseList.json")
        browse_list_has_error = True

    browse_list_parent_uuids = set()
    for screen in screens:
        parent_uuid = screen['screenUrl']
        if parent_uuid in browse_list_parent_uuids:
            print(u"Duplicate screen: {}".format(parent_uuid).encode("utf-8"))
            browse_list_has_error = True
            continue
        browse_list_parent_uuids.add(parent_uuid)

    if browse_list_parent_uuids:
        print(u"Screens listed in browseList.json:")
        for parent_uuid in browse_list_parent_uuids:
            print(parent_uuid)

    if browse_list_has_error:
        print(u"browseList.json has errors")
    else:
        print(u"browseList.json is good")

    return browse_list_has_error, browse_list_parent_uuids, screens


def validate_parent_uuid_folders():
    print(u"\n")
    print "Identified parent UUIDs: "
    parents = []
    for entry in entries:
        if entry.name.endswith("/"):
            entry_name = get_directory_name(entry.name)
            if len(entry_name) == 36:
                parents.append(entry)
                print entry_name

    print "\n"
    print "Validating each parent UUID folder:"
    browse_list_screens_validated = {}
    for parent in parents:
        result = validate_parent_folder(bucket, parent)
        parent_uuid = get_directory_name(parent.name)
        if "/screen/" + parent_uuid in browse_list_parent_uuids:
            if result:
                browse_list_screens_validated["/screen/" + parent_uuid] = True

    return browse_list_screens_validated


def validate_browse_list_icons(browse_list_screens_validated):
    print "\n"
    print(u"Check if the screens in browseList.json have icons in S3")
    for screen in screens:
        display_icon_path = screen['displayIcon']
        if not bucket.get_key("screensConfig/screens/" + display_icon_path):
            print(u"{} NO".format(screen.get('screenUrl')).encode("utf-8"))
            if browse_list_screens_validated.get(screen.get('screenUrl')):
                browse_list_screens_validated[screen.get('screenUrl')] = False
        else:
            print(u"{} YES".format(screen.get('screenUrl')).encode("utf-8"))


if __name__ == '__main__':

    parser = OptionParser(description="Specify -l to test local files only. Otherwise it tests deployed files only.\n"
                                      "Set DEPLOY_ENV environment parameter to stage, prod or canary to run against \n"
                                      "that specified environment, when running in default mode.\n"
                                      "Uses boto, so make sure to set the environment as required using any of the \n"
                                      "options: http://boto.cloudhackers.com/en/latest/boto_config_tut.html")

    parser.add_option("-l", "--local",
                      action="store_true", dest="local_only", default=False,
                      help="test local files only")

    (options, args) = parser.parse_args()

    if options.local_only:
        validate_local_screen_configs()
        exit(0)

    bucket_name = ""
    env = os.getenv("DEPLOY_ENV")
    if env == "canary":
        bucket_name = "quixey-canary"
    elif env == "stage":
        bucket_name = "quixey-stage"
    elif env == "prod":
        bucket_name = "quixey-prod"
    else:
        print "Unknown environment: DEPLOY_ENV={}".format(env)
        exit(1)

    print "DEPLOY_ENV is {}. Using bucket: {}".format(env, bucket_name)

    s3_connection = boto.connect_s3()
    bucket = s3_connection.get_bucket(bucket_name)

    result, browse_list_parent_uuids, screens = validate_browse_list()

    """
    {
      "screenUrl": "/screen/aaf6c742-0a58-4a62-88c9-8b40d4e49e04",
      "displayName": "News",
      "displayIcon": "4041472252/assets/USAScreenIcon.png",
      "ownerId": "4041472252",
      "isDefault": false
    }
    """

    entries = bucket.list("screensConfig/screens/4041472252/", "/")

    browse_list_screens_validated = validate_parent_uuid_folders()

    validate_browse_list_icons(browse_list_screens_validated)

    screen_id_to_name_map = {}
    for screen in screens:
        screen_id_to_name_map[screen['screenUrl']] = screen['displayName']

    print(u"\n")
    print(u"Summary of screens in browseList.json")
    for parent_uuid in browse_list_parent_uuids:
        if not browse_list_screens_validated.get(parent_uuid):
            print(u"FAIL {}: {}".format(parent_uuid, screen_id_to_name_map[parent_uuid]).encode("utf-8"))
        else:
            print(u"PASS {}: {}".format(parent_uuid, screen_id_to_name_map[parent_uuid]).encode("utf-8"))

    print(u"\n")
    print "DONE"
