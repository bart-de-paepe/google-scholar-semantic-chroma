import re
from datetime import datetime, timezone

from httpx import Client
from pymupdf import pymupdf


def escape_double_quotes(string):
    string = string.replace('"', '\"')
    return string

def undo_escape_double_quotes(string):
    string = string.replace('\"', '"')
    return string

def do_external_request(url, follow_redirect):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,lt;q=0.8,et;q=0.7,de;q=0.6",
    }
    client = Client(headers=headers, follow_redirects=follow_redirect)
    response = client.get(url)
    return response

def search_in_text(text, link):
    # find using regex
    patterns = get_patterns()
    doi_result = None
    while (doi_result is None) and (len(patterns) > 0):
        doi_result = re.search(patterns.pop(), text, re.IGNORECASE)

    if doi_result is not None:
        # update DOI
        doi = doi_result.group(0)
        link.doi = doi
        link.is_doi_success = True
        link.log_message = "DOI successfully retrieved"

def search_in_pdf(pdf, link):
    doc = pymupdf.Document(stream=pdf)
    # Extract all Document Text
    text = chr(12).join([page.get_text() for page in doc])
    patterns = get_patterns()
    doi_result = None
    while (doi_result is None) and (len(patterns) > 0):
        pattern = re.compile(patterns.pop(), re.IGNORECASE)
        doi_result = pattern.search(text)

    if doi_result is not None:
        #update DOI
        doi = doi_result.group(0)
        link.doi = doi
        link.is_doi_success = True
        link.log_message = "DOI successfully retrieved"

def search_in_pdf_file(pdf, link):
    print("search_in_pdf_file " + pdf)
    doc = pymupdf.open(pdf, filetype="pdf")
    # Extract all Document Text
    text = chr(12).join([page.get_text() for page in doc])
    patterns = get_patterns()
    doi_result = None
    while (doi_result is None) and (len(patterns) > 0):
        pattern = re.compile(patterns.pop(), re.IGNORECASE)
        doi_result = pattern.search(text)

    if doi_result is not None:
        #update DOI
        doi = doi_result.group(0)
        link.doi = doi
        link.is_doi_success = True
        link.log_message = "DOI successfully retrieved"

def get_patterns():
    # https://www.crossref.org/blog/dois-and-matching-regular-expressions/
    # /^10.\d{4,9}/[-._;()/:A-Z0-9]+$/i
    # /^10.1002/[^\s]+$/i
    # /^10.\d{4}/\d+-\d+X?(\d+)\d+<[\d\w]+:[\d\w]*>\d+.\d+.\w+;\d$/i
    # /^10.1021/\w\w\d++$/i
    # /^10.1207/[\w\d]+\&\d+_\d+$/i

    patterns = [r"10.1207/[\w\d]+\&\d+_\d+", r"10.1021/\w\w\d++",
                r"10.\d{4}/\d+-\d+X?(\d+)\d+<[\d\w]+:[\d\w]*>\d+.\d+.\w+;\d", r"10.1002/[^\s]+",
                r"10.\d{4,9}/[-._;()/:A-Z0-9]+"]
    return patterns

def printable_date_time_now():
    current_datetime = datetime.now(timezone.utc)
    return current_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")