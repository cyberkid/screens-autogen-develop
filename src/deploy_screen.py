from optparse import OptionParser
import sys
import screen_generator
import json
import codecs
import boto
from boto.s3.key import Key
from pprint import pprint as pp
import subprocess
from subprocess import Popen, PIPE
import watchdog
import os
import re

reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

PARTNER_ID = os.environ.get('PARTNER_ID', 4041472252)
S3_CFG_PATH = os.environ.get('S3_CFG_PATH', "~/.s3cfg")
S3CMD_PATH = os.environ.get('S3CMD_PATH', "/usr/local/bin/s3cmd")

def deploy_screen(options):
    cfg_file = os.path.abspath(options.cfg_file)
    if os.path.exists(os.path.abspath(options.output_path)) == False:
        os.makedirs(os.path.abspath(options.output_path))
    screen_generator.generate_screen_configs(options, cfg_file)
    with codecs.open(cfg_file, "r", "utf-8") as config_file:
        screen_cfg_data = json.load(config_file, "utf-8")
        s3path = "s3://quixey-canary/screensConfig/screens/"+screen_cfg_data['partnerid']+"/"+screen_cfg_data['screen-uuid']+"/config/"
        gen_screen_file_name = screen_cfg_data['screen-file-name']
        gen_screen_zip_file_name = screen_cfg_data['screen-file-name']+ ".gz"

        screen_child_uuid = ""
        m = re.search("^([a-f0-9\-]+)\.json", gen_screen_file_name)
        if not m:
            print("########\n########\nWARNING: invalid screen-file-name not UUID.json: <{}>\n#######\n#######".format(gen_screen_file_name))
            return(0) ##### REVIEW/FIX/HACK/MAYBE EXCEPT???? EXIT???? ######

        screen_child_uuid = m.group(1)
        base_path = os.path.abspath(options.output_path)
        screen_meta_file_path = base_path + "/" + screen_child_uuid + "_meta.json"

        deploy_screen_Zip_To_S3(s3path,os.path.abspath(options.output_path)+"/"+gen_screen_zip_file_name)
        print "Zipped Screen definition '"+gen_screen_file_name+".gz' deployed at location "+s3path+" under s3 bucket 'quixey-canary'"

        deploy_screen_To_S3(s3path+gen_screen_file_name,os.path.abspath(options.output_path)+"/"+gen_screen_file_name)
        print "Screen definition '"+gen_screen_file_name+"' deployed at location "+s3path+" under s3 bucket 'quixey-canary'"

        # deploy the meta_screen

        deploy_screen_To_S3(s3path, screen_meta_file_path)
        print "Screen definition '" + screen_meta_file_path + "' deployed at location " + s3path + " under s3 bucket 'quixey-canary'"

def deploy_screen_To_S3(s3path,screen_file_path) :
    upload_screen_config_command = \
        "{} -c {} put {} {}".format(S3CMD_PATH, S3_CFG_PATH, screen_file_path, s3path)
    upload_screen_config_args = [
        S3CMD_PATH, "-c", S3_CFG_PATH, "put", screen_file_path, s3path
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

def deploy_screen_Zip_To_S3(s3path,screen_file_path) :

    upload_screen_config_gz_command = \
        "{} -c {} --add-header='Content-Encoding: gzip' put {} {}" \
            .format(S3CMD_PATH, S3_CFG_PATH, screen_file_path, s3path)
    upload_screen_config_gz_args_old = [
        S3CMD_PATH, "-c", S3_CFG_PATH, "--add-header=\'Content-Encoding: gzip\'", "put", screen_file_path, s3path
    ]

    upload_screen_config_gz_args = [
        S3CMD_PATH, "-c", S3_CFG_PATH, "put", screen_file_path, s3path
    ]

    try:
        print "Executing command: {}".format(upload_screen_config_gz_command)

        # result = subprocess.call(upload_screen_config_command, shell=True)
        p = Popen(upload_screen_config_gz_args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate(b"input data that is passed to subprocess' stdin")
        rc = p.returncode

        print output, err
        if rc is not 0:
            print(u"Failure")
        else:
            print(u"Success")
    except subprocess.CalledProcessError as e:
        print(u"Exception occured: {}".format(e.message).encode("utf-8"))
        print(u"Failed executing command: {}".format(upload_screen_config_gz_command).encode("utf-8"))

    # print screen_file_path
    # s3_connection = boto.connect_s3()
    # bucket = s3_connection.get_bucket("quixey-canary")
    # key = boto.s3.key.Key(bucket, s3path)
    # key.metadata = {"Content-Type":"application/json","Content_Encoding":"gzip"}
    # with open(screen_file_path,"rb") as f:
    #     key.set_contents_from_file(f)


if __name__ == "__main__":

    parser = OptionParser(
        description="deploy screen configurations\n"
                    "-c option should be specified. \n"
    )

    parser.add_option("-c", "--cfg_file", dest="cfg_file",
                      help="the screens config file to deploy to canary")
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="enable debug")
    parser.add_option("-x", dest="rss_local")

    parser.add_option("-o", "--output_path", dest="output_path", help="Output path", default="gen-screens")

    parser.add_option("-t", "--test_run", dest="test_run", action="store_true", default=False)

    (options, args) = parser.parse_args()

    deploy_screen(options)