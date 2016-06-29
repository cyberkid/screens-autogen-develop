from optparse import OptionParser
import os
import json
from collections import Counter
import pprint
import glob
import codecs
from pprint import pprint as pp
import subprocess
from subprocess import Popen, PIPE
import watchdog
import re
from screen_builder import screen_builder

# Fix UTF-8 problems
import sys
reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

# The following imports are necessary to get these classes dynamically

from fetchers import fetcher_RSS
from fetchers import fetcher_single
from fetchers import fetcher_youtube
from fetchers import fetcher_bleacherreport
from fetchers import fetcher_facebook
from fetchers import fetcher_toi
from fetchers import fetcher_vogue_in
from fetchers import fetcher_cosmopolitan
from fetchers import fetcher_css_selector
from fetchers import fetcher_hungryforever
from fetchers import fetcher_eattreatonline
from fetchers import fetcher_makemytrip
from fetchers import fetcher_thrillophillia
from fetchers import fetcher_feminismindia
from fetchers import fetcher_allrecipes
from fetchers import fetcher_dubeat
from fetchers import fetcher_ngobox
from fetchers import fetcher_universityex
from fetchers import fetcher_elephantjournal
from fetchers import fetcher_youthincmag
from fetchers import fetcher_highexistence
from fetchers import fetcher_speakingtree
from fetchers import fetcher_spiritscience
from fetchers import fetcher_scienceandnonduality
from fetchers import fetcher_trulymadly
from fetchers import fetcher_huffington
from fetchers import fetcher_yourtango
from fetchers import fetcher_tarshi
from fetchers import fetcher_betterindia
from fetchers import fetcher_logicalindian
from fetchers import fetcher_mansworld
from fetchers import fetcher_donothing
from fetchers import fetcher_divyabhaskar_sports
from fetchers import fetcher_divyabhaskar_bollywood
from fetchers import fetcher_divyabhaskar

from furl_generators import furl_generator_embedly_rss

from datadog import initialize
from datadog import api

options = {
    'api_key':'2a94ec7e9fc5220705c9ed0a7bffb6fe',
    'app_key':'affe414189ef461dd2f2ca4df7d3446bd66261de'
}

initialize(**options)

# USAGE
# -c <screen_config_file>
# [-d] enable debug - default disabled
# [-t] enable test mode - do not write output files, write to std out instead default false
# [-x] <directory to use as local cache for fetching - files will be: "feedname.X" where X is determined buy the fetcher
#         we do not recommend spaces in the feedNames if you plan to use -x
# [-p] enable "prefetch" for cloud functions
# [-o <outputpath>] specifies the output path for the generated files - NOTE: default is ./

# note - the master config
debug = 0

PARTNER_ID = os.environ.get('PARTNER_ID', 4041472252)
S3_CFG_PATH = os.environ.get('S3_CFG_PATH', "~/.s3cfg")
S3CMD_PATH = os.environ.get('S3CMD_PATH', "/usr/local/bin/s3cmd")


def import_fetchers():
    # NOTE - need to get this to work
    # we want to get all of the fetcher_X.py files in the fetchers directory
    mypath = os.path.abspath(os.path.join(os.path.dirname(__file__), "./fetchers/"))
    myfetcher_files = [name for name in glob.glob(os.path.join(mypath, 'fetcher_*.py')) if
                       os.path.isfile(os.path.join(mypath, name))]


def generate_screen_configs(options, cfg_file):
    """
    Generate screen config file, and the gzipped file

    :param options: command line options
    :param cfg_file: screen generation config file
    :return:
    """

    ### Step 1: load the config

    sources = []
    all_results = dict()
    with codecs.open(cfg_file, "r", "utf-8") as CFGF:
        screen_cfg_data = json.load(CFGF, "utf-8")


    ### Step 2: iterate and fetch and generate furls
    for source_cfg in screen_cfg_data['sources']:
        name = source_cfg['name']

        enabled = source_cfg['enabled']
        if not enabled:
            print(u"Skipping screen name: <{}> since not enabled".format(name).encode("utf-8"))
            continue

        sources.append(name)
        # lets get the results
        # lets get the fetcher reference

        fetcher_name = "fetcher_" + source_cfg['fetcher']
        module = globals()[fetcher_name]

        try:
            function_reference = getattr(module, "fetch")
            all_results[name] = function_reference(source_cfg, options)
        except Exception, e:
            print "failed to run fetcher '"+fetcher_name+"', msg :"+e.message
            continue

        # print(u"Got {} results for <{}>".format(len(all_results[name]), name))
        # pprint.pprint(all_results[name])

        # now to FURLize :-)
        if "furl_generator" in source_cfg and source_cfg['furl_generator']:
            furl_generator_name = "furl_generator_" + source_cfg['furl_generator']
            module = globals()[furl_generator_name]
            function_reference = getattr(module, "add_furls")
            function_reference(all_results[name])
        print(u"Got {} results for <{}>".format(len(all_results[name]), name))
        if debug:
            pprint.pprint(all_results[name])


    ### Step 3 Generate the screen data in tabs

    # screen_result_data[tag]

    # for interleave ranking
    # we iterate across each source in the all_results
    # we store the current index for each source in source_index
    # for each iteration we keep track of how many results we added - if any, if none we are done!

    screen_result_data = dict()
    source_indexes = Counter()
    total_results = 0
    # for each iteration we keep track of if we added any - we stop when we didn't add any more
    added = 1
    for source_name in all_results.keys():
        # source_counts[source_name] = len(all_results[source_name])
        total_results += len(all_results[source_name])
        source_indexes[source_name] = 0

    if total_results > 0:
        added = 1  # for first pass only!

    while added:
        added = 0
        for source_name in all_results.keys():
            # we check if the len is more than the index
            if len(all_results[source_name]) > source_indexes[source_name]:
                added = 1
                next_result = all_results[source_name][source_indexes[source_name]]
                source_indexes[source_name] += 1

                tags = []
                if screen_cfg_data['include_all']:
                    tags = ["All"]
                tags.extend(next_result["tags"])

                for tag in tags:
                    if tag not in screen_result_data:
                        print(u"Adding tag: <{}>".format(tag).encode("utf-8"))
                        screen_result_data[tag] = []
                    screen_result_data[tag].append(next_result)

    if debug:
        print(u"Build screen_result_data:")
        pprint.pprint(screen_result_data)

    # now lets save the screen!
    meta_file = screen_builder.build_screen(screen_result_data, screen_cfg_data, options)
    return meta_file

def deploy_config_to_env(env, cfg_files, output_path, debug=False):
    """
    Deploy screen config files (json and gzipped json) to S3 destination appropriate to the env

    :param env: stage or canary or prod. Determines S3 bucket name
    :param cfg_files: A list of screen generation configuration files, used to determine paths locally and on S3
    :param output_path: The folder where the generated screen config files are stored
    :param debug: If True, print debugging info
    :return:
    """

    # There are three files: X.json, X.json.gz and X_meta.json

    print(u"Deploying to {}".format(env).encode("utf-8"))

    for cfg_file in cfg_files:
        # Get the screen generator config file path, and its template
        screen_generator_config_file_path = os.path.abspath(cfg_file)
        screen_generator_config_file_name, _ = os.path.splitext(screen_generator_config_file_path)
        screen_generator_config_folder = os.path.dirname(screen_generator_config_file_path)
        screen_generator_config_template_file_path = \
            os.path.join(screen_generator_config_folder, screen_generator_config_file_name + "-cfg.json")

        print "\n--------"
        print screen_generator_config_file_path, screen_generator_config_template_file_path

        with open(cfg_file) as cfg_file_object, \
                open(screen_generator_config_template_file_path) as cfg_template_file_object:
            cfg_file_content = json.load(cfg_file_object)
            cfg_template_file_content = json.load(cfg_template_file_object)

            # Get the parent screen guid. This is required to figure out the s3 destination folder
            screen_id_parts = cfg_template_file_content['screenId'].split("/")
            parent_screen_guid = screen_id_parts[len(screen_id_parts) - 1]

            if debug:
                print "\n"
                print cfg_file + ":"
                pp(cfg_file_content)

                print "\n"
                print screen_generator_config_template_file_path + ":"
                pp(cfg_template_file_content)

                print "\n"
                print "Parent Screen GUID: " + parent_screen_guid

            # Get paths to the generated screen config files
            screen_config_file_path = os.path.abspath(os.path.join(output_path, cfg_file_content['screen-file-name']))
            screen_config_file_name  = os.path.basename(screen_config_file_path)
            screen_config_file_gz_path = os.path.abspath(os.path.join(output_path, screen_config_file_name + ".gz"))
            screen_child_uuid = ""
            m = re.search("^([a-f0-9\-]+)\.json", cfg_file_content['screen-file-name'])
            if not m:
                print("########\n########\nWARNING: invalid screen-file-name not UUID.json: <{}>\n#######\n#######".format(cfg_file_content['screen-file-name']))
                return(0) ##### REVIEW/FIX/HACK/MAYBE EXCEPT???? EXIT???? ######
            else:
                screen_child_uuid = m.group(1)
                screen_config_meta_file_path = os.path.join(output_path, screen_child_uuid + "_meta.json")

            print "\n"
            print "screen_config_file_path: " + screen_config_file_path

            # check if screen has minimum number of furls. If not, skip deploy.
            urlcount=0
            expectedUrlCount = 5
            with codecs.open(screen_config_file_path, "r", "utf-8") as screen_config_file:
                screen_data = json.load(screen_config_file, "utf-8")
                for cardWidget in screen_data['cardListWidgets']:
                    for funcUrl in cardWidget['funcUrls']:
                        for dvUrl in funcUrl['dvUrls']:
                            urlcount=urlcount+1;

            if (urlcount<expectedUrlCount):
                title = "generated screen status"
                text = "screen '"+cfg_file_content['screen-file-name']+" ("+cfg_file_content['displayName']+")' not deployed as it has fewer ("+str(urlcount)+") deep view urls than expected min limit ("+str(expectedUrlCount)+")"
                tags = ['autogen:screenstatus:'+env]
                api.Event.create(title=title, text=text, tags=tags)
                print text
                continue

            print "screen_config_file_gz_path: " + screen_config_file_gz_path
            print "screen_config_meta_file_path: " + screen_config_meta_file_path

            # Figure out S3 bucket based on env
            if env == "stage":
                bucket = "quixey-stage"
            elif env == "canary":
                bucket = "quixey-canary"
            elif env == "prod":
                bucket = "quixey-prod"
            else:
                raise Exception("Environment not recognized: " + env)

            # Figure out S3 destination folder to which we copy the various screen generated configs
            s3_destination_folder = "s3://{}/screensConfig/screens/{}/{}/config/".format(bucket, PARTNER_ID, parent_screen_guid)

            # Upload screen config
            upload_screen_config_command = \
                "{} -c {} put {} {}".format(S3CMD_PATH, S3_CFG_PATH, screen_config_file_path, s3_destination_folder)
            upload_screen_config_args = [
                S3CMD_PATH, "-c", S3_CFG_PATH, "put", screen_config_file_path, s3_destination_folder
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

            # Upload screen config in gzipped format
            upload_screen_config_gz_command = \
                "{} -c {} --add-header='Content-Encoding: gzip' put {} {}"\
                    .format(S3CMD_PATH, S3_CFG_PATH, screen_config_file_gz_path, s3_destination_folder)
            upload_screen_config_gz_args_old = [
                S3CMD_PATH, "-c", S3_CFG_PATH, "--add-header=\'Content-Encoding: gzip\'", "put", screen_config_file_gz_path, s3_destination_folder
            ]

            upload_screen_config_gz_args = [
                S3CMD_PATH, "-c", S3_CFG_PATH, "put", screen_config_file_gz_path, s3_destination_folder
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

            # Upload screen_meta config
            upload_screen_config_command = \
                "{} -c {} put {} {}".format(S3CMD_PATH, S3_CFG_PATH, screen_config_meta_file_path, s3_destination_folder)
            upload_screen_config_args = [
                S3CMD_PATH, "-c", S3_CFG_PATH, "put", screen_config_meta_file_path, s3_destination_folder
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

if __name__ == "__main__":

    # global debug

    parser = OptionParser(
        description="Generates screens and deploys to the specified environment.\n"
                    "Either -c option should be specified or either -e or -g. \n"
                    "-c option cannot be specified along with -e or -g\n"
                    "When -g is specified, and -e is not, screen config files are generated but not deployed\n"
                    "If -u option is specified the generated config files are not uplaoded to S3"
    )

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="enable debug")

    parser.add_option("-c", "--cfg_file", dest="cfg_file",
                      help="the screens config file to load")

    parser.add_option("-e", "--environment", dest="env",
                      help="the environment to deploy to")

    parser.add_option("-g", "--group", dest="group",
                      help="the group to deploy")

    parser.add_option("-u", "--no-upload", dest="should_upload", action="store_false", default=True,
                      help="should upload files to the env specific S3 bucket")

    parser.add_option("-t", "--test_run", dest="test_run", action="store_true", default=False)

    parser.add_option("-T", "--timeout", dest="timeout", default=600, type="int",
                      help="Timeout in seconds - watchdog will kill program after timeout seconds", )

    parser.add_option("-x", dest="rss_local")

    parser.add_option("-p", "--prefetch", dest="prefetch", action="store_true", default=False,
                      help="prefetch the cloud-functions in the generated screen from canary")

    parser.add_option("-o", "--output_path", dest="output_path", help="Output path", default="./")

    (options, args) = parser.parse_args()

    if options.debug:
        debug = 1

    timeout = options.timeout

    if debug:
        print(u"Debug is enabled, timeout is: {}")

    if timeout > 0:
        print("Setting a timeout of: {} seconds.".format(timeout))
        watchdog = watchdog.Watchdog(timeout)
    # Step 1: load the config
    # Step 2: iterate across each feed/source and update results
    # Step 3: Construct the screen
    # Step 4: Write out the screen

    # Step 0: set up the structures
    # we have the following:
    # sources array of source_names
    # all_results a dict of source_name -> results
    # screen_result_data a dict of tabs -> results
    # screen_cfg_data -> JSON screen cfg

    if options.cfg_file and (options.env or options.group):
        raise parser.error("options incorrect")

    if not options.cfg_file and not (options.env or options.group):
        raise parser.error("options incorrect")

    env = None
    cfg_files = { options.cfg_file }

    if not options.cfg_file:
        env = options.env
        cfg_files = set()

        with open("config/deployment-cfg.json") as f:
            deployment_config = json.loads(f.read())

        if options.group:
            if env:
                if env in deployment_config['groups'][options.group]["envs"]:
                    for screen_config in deployment_config['groups'][options.group]["screens"]:
                        cfg_files.add(screen_config)
            else:
                for screen_config in deployment_config['groups'][options.group]["screens"]:
                    cfg_files.add(screen_config)
        else:
            for group_config in deployment_config['groups'].values():
                if env in group_config["envs"]:
                    for screen_config in group_config["screens"]:
                        cfg_files.add(screen_config)

        cfg_files_temp = set()
        for cfg_file in cfg_files:
            cfg_files_temp.add(os.path.join("config", cfg_file))
        cfg_files = cfg_files_temp

        if not cfg_files:
            print(u"No screens to generate")
            exit()

    if os.path.exists(options.output_path):
        if 0 and os.listdir(options.output_path):
            raise Exception("Output path: {} is not empty. Empty it and try again.".format(
                options.output_path).encode("utf-8"))
    else:
        os.makedirs(options.output_path)


    print(u"generating screens")
    for cfg_file in cfg_files:
        print(u"Generating for screen generator config: {}".format(cfg_file).encode("utf-8"))
        try:
            meta_file = generate_screen_configs(options, cfg_file)
            if env and options.should_upload:
                tempconfgarray = [cfg_file]
                deploy_config_to_env(env, tempconfgarray, options.output_path)
            else:
                print "Not deploying to any environment"
        except Exception, e:
            print "Screen generator failure', msg :"+ str(e)
            print("###########\n############\n###########\nFailed to generate screen from config: <{}>\n#######".format(cfg_file))

    if env is None:
        env = "none"
    title = "screens auto gen job status"
    text = 'finished screens auto gen job execution'
    tags = ['autogen:jobstatus:'+env]

    api.Event.create(title=title, text=text, tags=tags)

    watchdog.stop()