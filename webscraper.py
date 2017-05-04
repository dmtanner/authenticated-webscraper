#!/usr/bin/env python
""" Web Scraper for authenticated websites"""

import sys
import re
import requests
import io
from lxml import html
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
import pandas as pd
import numpy as np

USERNAME = "****"
PASSWORD = "****"

BASE_URL = "https://****.com"
LOGIN_URL = BASE_URL + "/login"
LOGIN_POST = BASE_URL + "/user_sessions"

class AuthenticatedPDFScraper():
    """ Used to retrieve and parse information from pdfs on authenticated websites. """

    def __init__(self, username, password, login_url, login_post):
        self.username = username
        self.password = password
        self.login_url = login_url
        self.login_post = login_post
        self.session = self.start_session()
        self.pdf_text = ""

    def start_session(self):
        """returns a new authenticated session"""
        session = requests.session()

        # Get login csrf token
        result = session.get(self.login_url)
        tree = html.fromstring(result.text)
        authenticity_token = list(
            set(tree.xpath("//meta[@name='csrf-token']/@content")))[0]

        # Create payload
        payload = {
            "user_session[email]": self.username,
            "user_session[password]": self.password,
            "authenticity_token": authenticity_token
        }

        # Perform login
        result = session.post(
            self.login_post, data=payload, headers=dict(referer=self.login_post))
        return session

    def get_pdf_text(self, pdf_url):
        """ Retrieve PDF from url and convert it to a string, store in object and return. """
        pdf_download = self.session.get(pdf_url)
        pdf = io.BytesIO(pdf_download.content)  #convert to bytes

        # PDFMiner boilerplate
        rsrcmgr = PDFResourceManager()
        sio = io.StringIO()
        codec = 'utf-8'
        laparams = LAParams()
        device = TextConverter(rsrcmgr, sio, codec=codec, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        # extract text
        for page in PDFPage.get_pages(pdf):
            interpreter.process_page(page)

        # Get text from StringIO
        self.pdf_text = sio.getvalue()
        return self.pdf_text

    def get_tag_value(self, tag_name, text):
        """return a json value from it's property name (used for broken json)"""
        tag_name = "\"" + tag_name + "\":"
        tag_index = text.find(tag_name)
        comma_index = text.find(',', tag_index)
        tag_substring = text[tag_index:comma_index]
        tag_value = tag_substring[len(tag_name):len(tag_substring)]
        return tag_value


    def get_post_element_value(self, element_name, text, start_index, must_contain):
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
            return self.get_post_element_value(element_name, text, bracket_index, must_contain)


    def get_js_variable(self, var_name, text):
        """return a javascript variable from it's name"""
        var_index = text.find(var_name)
        equal_index = text.find('=', var_index)
        semicolon_index = text.find(';', var_index)
        var_value = text[equal_index + 1:semicolon_index]
        var_value = var_value.replace('"', '')  #remove quotation marks
        return var_value

    def get_pdf_value(self, value_name, pdf_text):
        """ retrieve a value from a pdf file. """
        pdf_text = pdf_text.replace("\n\n", "\n")
        start_idx = pdf_text.find(value_name)
        if start_idx == -1:
            return ""
        sep_char = "\n"
        end_idx = pdf_text.find(sep_char, start_idx + len(value_name) + 1)
        value = pdf_text[start_idx:end_idx]
        value = value.replace(value_name, "")
        value = value.strip()
        return value




def main():

    # get command line arguments
    if len(sys.argv) < 3:
        print("Usage: webscraper.py input_file.csv output_file.csv")
        exit()

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # read in csv
    data = pd.read_csv(input_file)

    # create scraper
    scraper = AuthenticatedPDFScraper(USERNAME, PASSWORD, LOGIN_URL, LOGIN_POST)

    # perform scrape for each row in csv
    column_name = "Proposal URL"
    prop_url_idx = data.columns.get_loc(column_name)
    for row in data.values:
        try:
            # get pdf text
            html_pdf_url = row[prop_url_idx]
            pdf_url = "http://proposals.grow.com/pdf_generation/5620/" \
                + html_pdf_url[html_pdf_url.find(".com/") + 5:len(html_pdf_url)] + "/download"
            pdf_text = scraper.get_pdf_text(pdf_url)

            # parse pdf text
            grand_total = scraper.get_pdf_value("Grand\nTotal:", pdf_text)
            print("grand total: " + grand_total)
            discount = scraper.get_pdf_value("Discount", pdf_text)
            print("discount: " + discount)
            term = scraper.get_pdf_value("Term:", pdf_text)
            term_length = term[0:term.find(" ")]
            print("term length: " + term_length)
            auto_renew = False
            if term.find("auto-renew"):
                print("Auto Renew")
                auto_renew = True

            basic = False
            if pdf_text.find("Basic") != -1:
                print("Basic")
                basic = True

            trial = pdf_text.find("Trial\nPeriod:", pdf_text)
            print(trial)
            if trial != "":
                trial_period = trial[0:trial.find(" ")]
                print("trial period: " + trial_period)
            exit()

        except Exception as ex:
            print(ex)


if __name__ == '__main__':
    main()
