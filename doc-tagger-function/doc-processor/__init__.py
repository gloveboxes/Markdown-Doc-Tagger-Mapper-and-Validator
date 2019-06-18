
# az group create -l westus -n doc-tagger
# az storage account create -n doctagger -g doc-tagger -l westus --sku Standard_LRS --kind StorageV2
# az functionapp create --resource-group doc-tagger --os-type Linux \
# --consumption-plan-location westus  --runtime python \
# --name doc-tagger --storage-account  doctagger

# func azure functionapp publish doc-tagger --publish-local-settings --build-native-deps
# func azure functionapp publish doc-tagger  --build-native-deps


# https://github.com/Azure/azure-functions-core-tools/issues/954
# But, to answer your question, when you run func init and choose python, it will

# Verify you are in a venv through VIRTUAL_ENV environment variable.
# Verify your python version by running python --version
# Run pip install wheel
# Run pip install azure-functions azure-functions-worker
# Run pip freeze (which creates the requirements.txt file)
# May add your venv path to .funcignore if necessary (shouldn't matter in this case)

import logging
import json
import azure.functions as func
import os
import sys
import urllib.request
from bs4 import BeautifulSoup
import markdown2
from urllib.parse import urlparse, parse_qs, urlencode
import re
import base64
import requests


def main(req: func.HttpRequest) -> func.HttpResponse:

    data = None
    issues = []
    summary = []
    broken_links = 0

    try:
        req_body = req.get_json()
    except Exception as err:
        return func.HttpResponse(f'{err}', status_code=400)
    else:
        data = req_body

    app_json = json.dumps(data)

    tag_id = data.get('tag', None)
    absolute_url = data.get('baseUrl', '')
    validate_links = data.get('validate', "false")
    doc = data.get('doc', None)
    generate_html = data.get('htm', "false")

    if tag_id == None or doc == None:
        return func.HttpResponse(
            "JSON Error. Missing tag or doc or both",
            status_code=400
        )

    content = str(base64.b64decode(doc), 'utf-8')
    tracking_tag = 'WT.mc_id=' + tag_id

    def test_url(url):
        try:
            print(url)
            response = requests.get(url,
                                    allow_redirects=True, timeout=4)
            if response.status_code >= 400:
                return "Got HTTP response code {}".format(response.code)
        except Exception as e:
            return "Got exception {}".format(e)
        return None

    def validateUrls(url):
        if url.startswith('#'):
            return 0

        if not url.startswith('http'):
            return 0
            # url = base_url + url

        error = test_url(url)

        if error is not None:
            issues.append("{}: {}".format(error, url))
            return 1

        return 0

    def delete_existing_tags(content):

        links = re.findall(r"\[(.*?)\]\((.*?)\)", content)
        for link in links:

            result = urlparse(link[1])
            url = (result.netloc).lower()

            if url.find('microsoft.com') >= 0 or url.find('visualstudio.com') >= 0 or url.find('msdn.com') >= 0:
                query = result.query
                params = parse_qs(query)
                if params.pop('WT.mc_id', None) is None:
                    continue

                query = urlencode(params, doseq=True)

                find = "({})".format(link[1])
                if result.netloc == '':
                    if query == '':
                        replace = "({})".format(result.path)
                    else:
                        replace = "({}?{})".format(result.path, query)
                else:
                    if query == '':
                        replace = "({}://{}{})".format(result.scheme,
                                                       result.netloc, result.path)
                    else:
                        replace = "({}://{}{}?{})".format(result.scheme,
                                                          result.netloc, result.path, query)

                content = content.replace(find, replace)

        return content

    def convert_relative_to_absolute(content):
        links = re.findall(r"\[(.*?)\]\((.*?)\)", content)
        for link in links:
            result = urlparse(link[1])
            url = (result.netloc).lower()

            if url == '' and result.path != '':
                file_extension = os.path.splitext(result.path.lower())[1]

                if file_extension in ['.jpg', '.jpeg', '.png', '.gif']:
                    absolute_path = absolute_url + result.path
                    content = content.replace(
                        result.path, absolute_path)
                    continue

        return content

    def add_tracking_tag(content):
        links = re.findall(r"\[(.*?)\]\((.*?)\)", content)
        for link in links:
            result = urlparse(link[1])

            query = result.query
            url = (result.netloc).lower()

            if url.find('microsoft.com') >= 0 or url.find('visualstudio.com') >= 0 or url.find('msdn.com') >= 0:

                if query != '':
                    if query.find('WT.mc_id') < 0:
                        query = query + '&' + tracking_tag
                else:
                    query = tracking_tag

                find = "({})".format(link[1])
                replace = "({}://{}{}?{})".format(result.scheme,
                                                  result.netloc, result.path, query)

                content = content.replace(find, replace)

        return content

    def check_url_integrity(urls, headings):
        malformed_links = 0
        for url in urls:
            question = url.count('?')
            ampersand = url.count('&')

            if question > 1 or (ampersand > 0 and question != 1):
                issues.append("Malformed query string: {}".format(url))
                malformed_links += 1
            elif url.startswith('#'):
                search_id = url[1:]
                for heading in headings:
                    id = heading.get('id', None)
                    if id is not None:
                         if id == search_id:
                            break
                else:
                    issues.append("{}: {}".format(
                        "Internal link not found", url))
                    malformed_links += 1

        return malformed_links

    htm = markdown2.markdown(content,  extras=["header-ids"])
    soup = BeautifulSoup(htm, 'html.parser')

    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    urls = [a['href'] for a in soup.find_all('a', href=True) if a.text]

    malformed_links = check_url_integrity(urls, headings)

    content = delete_existing_tags(content)

    if absolute_url != '':
        content = convert_relative_to_absolute(content)

    if validate_links.lower() == 'true':
        # rebuild htm without the tracking tags
        htm = markdown2.markdown(content)
        soup = BeautifulSoup(htm, 'html.parser')

        urls = [a['href'] for a in soup.find_all('a', href=True) if a.text]

        for url in urls:
            broken_links += validateUrls(url)

        for img in soup.find_all("img"):
            if img["src"] != '':
                broken_links += validateUrls(img["src"])

    content = add_tracking_tag(content)
    data['doc'] = str(base64.b64encode(content.encode('utf-8')), 'utf-8')

    if generate_html == 'true':
        htm = markdown2.markdown(content, extras=[
                                 "header-ids", "tables", "fenced-code-blocks", "target-blank-links"])
        data['html'] = str(base64.b64encode(htm.encode('utf-8')), 'utf-8')

    data['issues'] = issues

    summary.append(f"Invalid Links: {malformed_links}")
    summary.append("Links not validated" if validate_links.lower()
                   != 'true' else f"Broken Links: {broken_links}")

    data['summary'] = summary

    app_json = json.dumps(data)

    if app_json:
        return func.HttpResponse(app_json, mimetype="application/json")
    else:
        return func.HttpResponse(
            "Please pass a name on the query string or in the request body",
            status_code=400
        )
