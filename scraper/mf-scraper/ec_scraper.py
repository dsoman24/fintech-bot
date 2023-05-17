## Motley Fool scraper
# https://www.crummy.com/software/BeautifulSoup/bs4/doc/

import requests
from bs4 import BeautifulSoup
from pprint import pprint
import os
import re

class MotleyFoolScraper:
    """
    Class contains the methods necessary to scrape
    """

    def scrape(self, url: str, write = False, print_info = False) -> bool:
        """
        Driver method. Scrapes the The Motley Fool Earning Call (EC) Transcript from a given url endpoint.
        Returns True if scrape was successful, False otherwise.
        url: the url of the EC Transcript on fool.com
        """

        url = url.strip()

        response = requests.get(url)

        if (response.status_code != 200): # catch invalid response and return False
            return False

        soup = BeautifulSoup(response.text, "html.parser")
        body = soup.find("div", {"class":"tailwind-article-body"})
        info = self.get_transcript_info(soup)
        all_tags = self.get_ec_body(body) # the list of the earning call tags text (main body)
        speakers = self.find_speakers(body)

        if print_info:
            print(f"================ {info} ================")

        for i, speaker in enumerate(speakers):
            if print_info:
                print(speaker)
            remarks = self.find_speaker_remarks(speakers, i, all_tags)
            if write:
                self.write_remark(speaker, remarks, info)
        if print_info:
            print()
        return True


    def ad_filter(self, tag):
            """
            Filter for ads or pitch containers
            """
            if tag.name == "br":
                return False
            elif tag.attrs.get("class") != None:
                return "interad" not in tag.attrs.get("class") and "article-pitch-container" not in tag.attrs.get("class")
            else:
                return True


    def get_ec_body(self, soup: BeautifulSoup):
        """
        Returns a list of all tags in the body between the prepared remarks and the q&a
        """

        # boundary_tags = soup.find_all(lambda tag: tag.name == "h2" and tag.text.lower() in ["prepared remarks:", "questions & answers:", "questions and answers:", "call participants:"])
        # start = boundary_tags[0]
        # end = boundary_tags[1]

        start = soup.find("h2")

        relevant_tags = []
        current_tag = start.next_sibling
        while current_tag != None:
            if current_tag.name is not None and self.ad_filter(current_tag):
                relevant_tags.append(current_tag)
            current_tag = current_tag.next_sibling

        return [tag.text for tag in relevant_tags]

    def get_transcript_info(self, soup):
        page_header = soup.find("h1", {"class": "font-medium text-gray-1100 leading-42 md:text-h1"}).text

        ticker_match = re.search(r"\((.*?)\)", page_header)
        quarter_match = re.search(r"Q(\d)\s(\d{4})", page_header)
        company_name = page_header[:ticker_match.start()].strip()
        ticker = ticker_match.group(1)
        quarter = int(quarter_match.group(1))
        year = int(quarter_match.group(2))
        return company_name, ticker, quarter, year

    def speaker_filter(self, tag):
        return tag.name == "p" and tag.find("strong") and "--" in tag.text.strip()


    def find_speakers(self, soup: BeautifulSoup):
        """
        Returns a list of internal speakers (Speaker Objects)
        soup: the BeautifulSoup object of the website to find the speakers
        """
        speakers = set()

        curr = soup.find("h2")
        while curr != None:
            if self.speaker_filter(curr) and self.ad_filter(curr):
                speaker_raw = curr.text.split(" -- ")
                # if (len(speaker_raw) == 2): # only get company speakers
                speakers.add(Speaker(curr.text)) # also gets q/a speakers, these will have two -- in their title
            curr = curr.next_sibling
        return list(speakers)


    def find_speaker_remarks(self, speakers, which, body):
        """
        Finds all speaker remarks for a given speaker in a list
        """
        speaker = speakers[which]
        indices = [] # first find indices in the body where this speaker begins speaking

        for i in range(len(body)):
            if body[i] == speaker.__str__():
                indices.append(i)

        speakers_text = [s.__str__() for s in speakers]
        remarks = []

        for index in indices:
            remark = ""
            i = index + 1
            while i < len(body) and body[i] not in speakers_text: # stop at the end of the doc or until a new speaker is reached
                remark += body[i] + "\n"
                i += 1
            remark = ".\n".join(remark.split(". "))
            remarks.append(remark)
        return remarks

    def write_remark(self, speaker, remarks, info):
        """
        Takes in a speaker and their remarks, and writes each section to a txt
        """
        # define the directory path and file name
        def format(string):
            return "-".join(string.split(" "))

        speaker_dir_name = format(speaker.name.lower()) + "_" + format(speaker.position.lower()) + "_" + str(speaker.asker)
        dir_path = f"./mfs-data/{info[1]}/{info[3]}/{info[2]}/{speaker_dir_name}/"
        # create the directory if it does not exist
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        for i, remark in enumerate(remarks):
            file_name = f"remark-{i}.txt"
            with open(os.path.join(dir_path, file_name), "w") as f:
                f.write(remark)

class Speaker:
    """
    Represents a speaker
    """
    def __init__(self, raw_format):
        self.html_text = raw_format
        split = raw_format.split(" -- ")
        self.name = split[0]
        if (len(split) < 2):
            self.position = "NONE"
        else:
            self.position = split[1]
        self.asker = False
        if len(split) == 3:
            self.asker = True

    def __eq__(self, other):
        return self.name == other.name and self.position == other.position

    def __hash__(self):
        return hash(self.name) + hash(self.position)

    def __str__(self):
        return self.html_text
