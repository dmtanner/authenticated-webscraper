#!/usr/bin/env python
""" Web Scraper for authenticated websites"""

import sys
import re
import requests
import io
from lxml import html
import PyPDF2 as pdf
import pandas as pd
import numpy as np

USERNAME = "****"
PASSWORD = "****"

BASE_URL = "https://****.com"
LOGIN_PAGE = BASE_URL + "/login"
LOGIN_URL = BASE_URL + "/user_sessions"


def get_tag_value(tag_name, text):
    """return a json value from it's property name (used for broken json)"""
    tag_name = "\"" + tag_name + "\":"
    tag_index = text.find(tag_name)
    comma_index = text.find(',', tag_index)
    tag_substring = text[tag_index:comma_index]
    tag_value = tag_substring[len(tag_name):len(tag_substring)]
    return tag_value


def get_post_element_value(element_name, text, start_index, must_contain):
    """return the text following a certain html element"""
    element_index = text.find(element_name, start_index)
    if element_index == -1:
        return "NOTFOUND"

    bracket_index = text.find('<', element_index + len(element_name))
    element_substring = text[element_index:bracket_index]
    element = element_substring[len(element_name):len(element_substring)]

    if element.find(must_contain) != -1:
        return element
    else:
        return get_post_element_value(element_name, text, bracket_index, must_contain)


def get_js_variable(var_name, text):
    """return a javascript variable from it's name"""
    var_index = text.find(var_name)
    equal_index = text.find('=', var_index)
    semicolon_index = text.find(';', var_index)
    var_value = text[equal_index + 1:semicolon_index]
    var_value = var_value.replace('"', '')  #remove quotation marks
    return var_value


def start_session():
    """returns a new authenticated session"""
    session = requests.session()

    # Get login csrf token
    result = session.get(LOGIN_PAGE)
    tree = html.fromstring(result.text)
    authenticity_token = list(
        set(tree.xpath("//meta[@name='csrf-token']/@content")))[0]

    # Create payload
    payload = {
        "user_session[email]": USERNAME,
        "user_session[password]": PASSWORD,
        "authenticity_token": authenticity_token
    }

    # Perform login
    result = session.post(
        LOGIN_URL, data=payload, headers=dict(referer=LOGIN_URL))
    return session


def main():

    if len(sys.argv) < 3:
        print("Usage: webscraper.py input_file.csv output_file.csv")
        exit()

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    data = pd.read_csv(input_file)

    session = start_session()

    col_idx = data.columns.get_loc("COLUMN NAME")
    for row in data.values:
        try:
            company_id = row[col_idx]
            search_url = BASE_URL + "/app?search=%s&status=accepted" % company_id
            print(company_id, end=' ')

            # Scrape search_url
            result = session.get(search_url)
            result_htmltree = html.fromstring(result.text)
            result_text = result.text

            # extract proposal_id
            prop_id = get_tag_value("proposal_id", result_text)
            print(prop_id)

            # download pdf
            prop_html_url = BASE_URL + "/app/proposals/" + prop_id
            prop_html = session.get(prop_html_url)
            prop_pdf_id = get_js_variable("base_proposal_path", prop_html.text)
            print("pdf_id: " + prop_pdf_id)
            prop_pdf_url = BASE_URL + "/pdf_generation/5620/" + prop_pdf_id + "/download"
            prop_pdf = session.get(prop_pdf_url)
            prop_pdf_bytes = io.BytesIO(prop_pdf.content)
            #prop_pdf = slate.PDF(prop_pdf)
            #print(prop_pdf.content)
            pdf_reader = pdf.PdfFileReader(prop_pdf_bytes)
            page_content = pdf_reader.getPage(6).extractText()
            print(page_content)

        except Exception as ex:
            print(ex)


if __name__ == '__main__':
    main()

