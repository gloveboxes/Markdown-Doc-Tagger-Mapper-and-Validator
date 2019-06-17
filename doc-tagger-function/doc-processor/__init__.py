
# az group create -l westus -n doc-tagger
# az storage account create -n doctagger -g doc-tagger -l westus --sku Standard_LRS --kind StorageV2
# az functionapp create --resource-group doc-tagger --os-type Linux \
# --consumption-plan-location westus  --runtime python \
# --name doc-tagger --storage-account  doctagger

# func azure functionapp publish doc-tagger --publish-local-settings --build-native-deps

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


def main(req: func.HttpRequest) -> func.HttpResponse:

    data = None
    issues = []
    summary = []
    broken_links = 0
    malformed_links = 0

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

    if tag_id == None or doc == None:
        return func.HttpResponse(
            "JSON Error. Missing tag or doc or both",
            status_code=400
        )

    content = str(base64.b64decode(doc), 'utf-8')
    tracking_tag = 'WT.mc_id=' + tag_id

    def test_url(url):
        try:
            req = urllib.request.Request(url, method='HEAD', headers={
                'User-Agent': "link-checker"})
            resp = urllib.request.urlopen(req, timeout=10)
            if resp.code >= 400:
                return "Got HTTP response code {}".format(resp.code)
        except Exception as e:
            return "Got exception {}".format(e)
        return None

    def check_query_string(url):
        question = url.count('?')
        ampersand = url.count('&')

        if question > 1:
            return 'Malformed query string'

        if ampersand > 0 and question != 1:
            return 'Malformed query string'

        return None

    def validateUrls(url):
        if url.startswith('#'):
            # url = base_url + url
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
        malformed_links = 0

        links = re.findall(r"\[(.*?)\]\((.*?)\)", content)
        for link in links:

            result = check_query_string(link[1])
            if result is not None:
                issues.append("{}: [{}]({})".format(result, link[0], link[1]))
                malformed_links += 1
                continue

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

        return content, malformed_links

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

    content, malformed_links = delete_existing_tags(content)

    if absolute_url != '':
        content = convert_relative_to_absolute(content)

    if validate_links.lower() == 'true':
        htm = markdown2.markdown(content)
        soup = BeautifulSoup(htm, 'html.parser')

        urls = [a['href']
                for a in soup.find_all('a', href=True) if a.text]

        for url in urls:
            broken_links += validateUrls(url)

        for img in soup.find_all("img"):
            if img["src"] != '':
                broken_links += validateUrls(img["src"])

    content = add_tracking_tag(content)
    data['doc'] = str(base64.b64encode(content.encode('utf-8')), 'utf-8')
    data['issues'] = issues

    summary.append(f"Malformed Query Strings: {malformed_links}")
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
