from optparse import OptionParser
import json
import codecs
import shutil
import sys
import os
import boto
import os.path
import re
reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

from pprint import pprint as pp
import subprocess
from subprocess import Popen, PIPE
import watchdog

PARTNER_ID = os.environ.get('PARTNER_ID', 4041472252)
S3_CFG_PATH = os.environ.get('S3_CFG_PATH', "~/.s3cfg")
S3CMD_PATH = os.environ.get('S3CMD_PATH', "/usr/local/bin/s3cmd")

def setup_screen_configs(cfg_file, output_path):

    m=re.search("([^\\\\/]+).json$", cfg_file)
    output_path_dir = os.path.abspath(output_path);
    master_config_file_path = os.path.abspath(output_path_dir+"/"+m.group(1)+"-cfg.json")
    cfg_file = os.path.abspath(cfg_file)
    screen_control_data_file_path = os.path.abspath("samples/ScreenControlData.json")

    shutil.copy2(os.path.abspath('samples/sample-master-cfg.json'), master_config_file_path)

    screen_cfg_data = ""

    with codecs.open(cfg_file, "r", "utf-8") as config_file:
        screen_cfg_data = json.load(config_file, "utf-8")
        tagsList=[]
        for tag in screen_cfg_data['tags']:
            tagsList.append(tag)
        with codecs.open(master_config_file_path, "r", "utf-8") as master_config_file_r:
            master_config_data = json.load(master_config_file_r, "utf-8")
            master_config_data['screenId'] = "/screen/"+screen_cfg_data['screen-uuid']
            master_config_data['displayName'] = screen_cfg_data['displayName']
            master_config_data['displayIcon'] = screen_cfg_data['partnerid'] + "/" + "assets" + "/" + screen_cfg_data['displayIcon']
            master_config_data['id'] =  screen_cfg_data['screen-file-name'].split(".")[0]
            master_config_data['tags'] = tagsList
        with codecs.open(screen_control_data_file_path, "r", "utf-8") as screen_control_data_file_r:
            screen_control_data = json.load(screen_control_data_file_r, "utf-8")
            screen_control_data['criteria'][0]['defaultPath'] = "config/"+screen_cfg_data['screen-file-name']
            screen_control_data['description'] = screen_cfg_data['description']
            screen_control_data['displayName'] = screen_cfg_data['displayName']
            screen_control_data['displayIcon'] = screen_cfg_data['partnerid'] + "/" + "assets" + "/" +screen_cfg_data['displayIcon']
            screen_control_data['owner'] = screen_cfg_data['partnerid']
            screen_control_data['id'] = "screen/"+screen_cfg_data['screen-uuid']
            screen_control_data['tags'] = tagsList
        with codecs.open(master_config_file_path, 'w', "utf-8") as master_config_file_w:
            master_config_file_w.write(json.dumps(master_config_data))
        with codecs.open(screen_control_data_file_path, 'w', "utf-8") as screen_cfg_data_file_w:
            screen_cfg_data_file_w.write(json.dumps(screen_control_data))
            s3path = "s3://quixey-canary/screensConfig/screens/"+screen_cfg_data['partnerid']+"/"+screen_cfg_data['screen-uuid']+"/config/"+"ScreenControlData.json"

        deploy_screen_control_data_file_To_env(s3path,screen_control_data_file_path)
        print "Generatd master config file and saved at location "+ os.path.abspath(master_config_file_path)
        print "Saved screen control data file at "+s3path+" under s3 bucket 'quixey-canary'"

        return screen_cfg_data

def deploy_screen_control_data_file_To_env(s3path,screen_control_data_file_path) :

    upload_screen_config_command = \
        "{} -c {} put {} {}".format(S3CMD_PATH, S3_CFG_PATH, screen_control_data_file_path, s3path)
    upload_screen_config_args = [
        S3CMD_PATH, "-c", S3_CFG_PATH, "put", screen_control_data_file_path, s3path
    ]
    try:
        print "Executing command: {}".format(upload_screen_config_command)

        # result = subprocess.call(upload_screen_config_command, shell=True)
        p = Popen(upload_screen_config_args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate(b"input data that is passed to subprocess' stdin")
        rc = p.returncode

        print output, err
        if rc is not 0:
            print(u"Failure")
        else:
            print(u"Success")
    except subprocess.CalledProcessError as e:
        print(u"Exception occured: {}".format(e.message).encode("utf-8"))
        print(u"Failed executing command: {}".format(upload_screen_config_command).encode("utf-8"))


    # s3_connection = boto.connect_s3()
    # bucket = s3_connection.get_bucket("quixey-canary")
    # key = boto.s3.key.Key(bucket, s3path)
    # with open(screen_control_data_file_path) as f:
    #     key.set_contents_from_file(f)

if __name__ == "__main__":

    parser = OptionParser(
        description="setups screen configurations\n"
                    "-c option should be specified.\n"
                    "-o output path should be specified \n"
    )

    parser.add_option("-c", "--cfg_file", dest="cfg_file",
                      help="the screens config file to set up")

    parser.add_option("-o", "--output_path", dest="output_path",
                      help="output dir to add generated files")


    (options, args) = parser.parse_args()

    if (options.cfg_file is None) :
        print "config file must be specified"
        sys.exit()
    if os.path.exists(os.path.abspath(options.cfg_file)) == False:
        print "config file doesn't exists at "+options.cfg_file
        sys.exit()
    if (options.output_path is None) :
        print "output dir must be specified"
        sys.exit()

    print os.path.abspath(options.output_path)
    if os.path.isdir(os.path.abspath(options.output_path)) == False:
        print "output dir doesn't exists "+options.output_path
        sys.exit()

    screen_cfg_json = setup_screen_configs(options.cfg_file, options.output_path)

    # now lets update the html file for this user
    # If the "file" exists PATH/user.html then simply append:
    #    <LI> <a href="screens://screen/SCREEN_ID">SCREEN_NAME</A> </LI>
    # and re-push with the "-P"
    user_name = screen_cfg_json['username']
    s3_html_path = "s3://quixey-dev/eglover/public/html/" + user_name + ".html"
    screen_uuid = screen_cfg_json['screen-uuid']
    screen_title = screen_cfg_json['displayName']
    # lets fetch the old file...
    # $ s3cmd get s3://quixey-dev/eglover/public/html/no-such-file.html .
    working_directory = options.output_path
    local_html_path = working_directory +  user_name + ".html"
    print("Attempting to retrieve old HTML file")

    try:
        os.remove(local_html_path)
    except OSError:
        pass

    fetch_html_file_command = \
        "{} -c {} get {} {}".format(S3CMD_PATH, S3_CFG_PATH, s3_html_path, working_directory)
    fetch_html_config_args = [
        S3CMD_PATH, "-c", S3_CFG_PATH, "get", s3_html_path, working_directory
    ]
    try:
        print "Executing command: {}".format(fetch_html_file_command)
    # result = subprocess.call(upload_screen_config_command, shell=True)
        p = Popen(fetch_html_config_args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate(b"input data that is passed to subprocess' stdin")
        rc = p.returncode

        print output, err
        if rc is not 0:
            print(u"Failure")
        else:
            print(u"Success")
    except subprocess.CalledProcessError as e:
        print(u"Exception occured: {}".format(e.message).encode("utf-8"))
        print(u"Failed executing command: {}".format(fetch_html_file_command).encode("utf-8"))
        # it is okay to fail the first time!!!

    print("Adding screen <{}>, <{}> to the html file: <{}>".format(screen_uuid, screen_title, local_html_path))
    if not os.path.isfile(local_html_path):
        print("file <{}> does not exist, creating!".format(local_html_path))
        html_file = "<title>Screens for user: " + user_name + "</title>\n"
        html_file += "<H1>Screens for user: " + user_name + "</H1>\n<UL>\n"
    else:
        with open(local_html_path, "r") as HF:
            html_file = HF.read()

    # check if the current screen is present, if so, done, else add it and write back

    m = re.search("%s" %screen_uuid, html_file)
    if not m:
        html_file += "\n<LI> <a href=\"screens://screen/" + screen_uuid + "\">" + screen_title + "</A></LI>\n"

        # now we write back the file to disk
        print("Saving back new file to: <{}>".format(local_html_path))
        with open(local_html_path, "w") as HF:
            HF.write(html_file)

        # now lets send the file back!
        print("Attempting to push new HTML file")

        push_html_file_command = \
            "{} -c {} -P put {} {}".format(S3CMD_PATH, S3_CFG_PATH, local_html_path, s3_html_path)
        push_html_config_args = [
            S3CMD_PATH, "-c", S3_CFG_PATH, "-P", "put", local_html_path, s3_html_path
        ]
        try:
            print "Executing command: {}".format(push_html_file_command)
        # result = subprocess.call(upload_screen_config_command, shell=True)
            p = Popen(push_html_config_args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            output, err = p.communicate(b"input data that is passed to subprocess' stdin")
            rc = p.returncode

            print output, err
            if rc is not 0:
                print(u"Failure")
            else:
                print(u"Success")
        except subprocess.CalledProcessError as e:
            print(u"Exception occured: {}".format(e.message).encode("utf-8"))
            print(u"Failed executing command: {}".format(push_html_file_command).encode("utf-8"))
            # it is okay to fail the first time!!!
    else:
        # we want to ensure the line is correct, so we remove that line and re-add the current one
        sub_value = screen_uuid + "\">" + screen_title + "</A"
        html_file = re.sub("%s\">([^\">]+)" %screen_uuid, sub_value, html_file)

        # now we write back the file to disk
        print("Saving back new file to: <{}>".format(local_html_path))
        with open(local_html_path, "w") as HF:
            HF.write(html_file)

        # now lets send the file back!
        print("Attempting to push new HTML file")

        push_html_file_command = \
            "{} -c {} --acl-public put {} {}".format(S3CMD_PATH, S3_CFG_PATH, local_html_path, s3_html_path)
        push_html_config_args = [
            S3CMD_PATH, "-c", S3_CFG_PATH, "--acl-public",  "put", local_html_path, s3_html_path
        ]
        try:
            print "Executing command: {}".format(push_html_file_command)
        # result = subprocess.call(upload_screen_config_command, shell=True)
            p = Popen(push_html_config_args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            output, err = p.communicate(b"input data that is passed to subprocess' stdin")
            rc = p.returncode

            print output, err
            if rc is not 0:
                print(u"Failure")
            else:
                print(u"Success")
        except subprocess.CalledProcessError as e:
            print(u"Exception occured: {}".format(e.message).encode("utf-8"))
            print(u"Failed executing command: {}".format(push_html_file_command).encode("utf-8"))
            # it is okay to fail the first time!!!
