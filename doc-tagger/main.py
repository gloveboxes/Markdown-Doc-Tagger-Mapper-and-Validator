# pyinstaller main.py -n doc-tagger --onefile

import base64
import requests
import json
import getopt
import sys
import os.path

doc_tagger_url = "https://doc-tagger.azurewebsites.net/api/doc-processor"
# doc_tagger_url = "http://localhost:7071/api/doc-processor"

filename = None
tag = None
base_url = ''
validate = False
htm = False
data = {}

doc_tagger_version = 1.0

running_in_docker = False

try:
    if os.environ['CA_DOC_TAGGGING_IN_DOCKER']:
        dir = "/docs"
        running_in_docker = True
except:
    dir = None


def usage():
    print('Mandatory arguments: -f Filename -t tag')
    print('Optional arguments: -b baseUrl -v validate urls -h generate html --help')
    print("\nExample: doc-tagger -f README.md -t devto-blog-alias -b https://raw.githubusercontent.com/GitHubName/Repository/master -v\n")
    sys.exit(2)


def main():
    global filename, tag, base_url, validate, doc_tagger_url, htm
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hf:t:b:ve:", ["help"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        # sys.exit(2)

    for o, a in opts:
        if o == '-f':
            filename = a.strip()
        elif o == "-v":
            validate = True
        elif o == "-h":
            htm = True
        elif o == '-t':
            tag = a.strip()
        elif o == "-b":
            base_url = a.strip()
        elif o == "-e":
            doc_tagger_url = a.strip()
        elif o in ("--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    if filename == None or tag == None:
        usage()

    if running_in_docker:
        filename = os.path.join(dir, filename)

    if not os.path.isfile(filename):
        print(f'File not found: {filename}')
        usage()


def build_request():
    global data, filename, tag, base_url, validate
    data['baseUrl'] = base_url
    data['tag'] = tag
    data['validate'] = "true" if validate else "false"
    data['htm'] = "true" if htm else "false"
    data['version'] = doc_tagger_version

    with open(filename) as f:
        content = f.read()
        data['doc'] = str(base64.b64encode(content.encode('utf-8')), 'utf-8')


def call_doc_tagger_function(data):
    global filename, tag

    print("\nRebasing relative image links to absolute links" if base_url != '' else "")
    print("\nProcessing with link validation. This will take a few moments..." if validate else "\nProcessing...")

    json_data = json.dumps(data)
    response = requests.post(doc_tagger_url, data=json_data)

    if(response.ok):
        json_data = json.loads(response.text)

        out_filename = filename + '.' + tag + '.md'
        with open(out_filename, "w") as o:
            data = str(base64.b64decode(json_data['doc']), 'utf-8')
            o.write(data)

        if htm:
            out_filename = filename + '.' + tag + '.html'
            with open(out_filename, "w") as o:
                data = str(base64.b64decode(json_data['html']), 'utf-8')
                o.write(data)   

        print("\nNo issues found." if len(
            json_data['issues']) == 0 else "\nIssues Found!\n")

        for issue in json_data['issues']:
            print(issue)
            print()

        print("\nSummary")
        print("==================================")

        for item in json_data['summary']:
            print(item)

        print()

        return len(json_data['issues'])

    else:
        print(
            f'Call to Doc Tagger Azure Function Failed: {response}, {response.text}')


def set_exit_status(issues):
    sys.exit(issues)


if __name__ == "__main__":
    print(f'\nDoc Tagger Version {doc_tagger_version}')
    main()
    build_request()
    issue_count = call_doc_tagger_function(data)
    set_exit_status(issue_count)
