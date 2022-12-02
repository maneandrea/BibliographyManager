import urllib.request
import lxml.html
import json
import time
import os
import re
from datetime import date
import threading

def __init__(self):
    return

APIURL = "http://inspirehep.net/api/"
ARXIVURL = "https://arxiv.org/list/{}/new"
ARXIVAPI = "http://export.arxiv.org/api/"
#Time to wait between requests to the Inspire API after the 50th
TIME_INTERVAL = 0.501 #seconds

class Query:
    def __init__(self):
        self.contents = None

    @classmethod
    def get(cls, query, verbose = 1):
        """Given the arxiv number of a paper requests the Bibtex entry to Inspire's API"""
        def pprint(arg, verbosity = 1):
            #Prints only if the argument verbose of get is bigger than the verbosity of the message
            if verbose > verbosity:
                print(arg)

        if re.match(r"(.+):\d{4}[a-zA-Z]+", query):
            request = f'literature/?q={query}&format=bibtex'.replace(' ', '').replace(':', '%3A')
        elif re.match(r"(\d{4}\.\d+)|([a-z-]+/\d+)", query):
            request = f'arxiv/{query}?format=bibtex'.replace(' ', '')
        else:
            pprint("The query '{}' must match an arxiv identifier or an inspire label".format(query), 0)
            raise cls.PaperNotFound

        url = APIURL + request

        pprint("Now requesting...")
        try:
            f = urllib.request.urlopen(url)
            pprint("Request successful, reading data...")
            bibtex = f.read().decode('utf-8')
        except urllib.error.HTTPError as err:
            if err.reason == 'Too Many Requests':
                time.sleep(TIME_INTERVAL)
                pprint("Too many requests, waiting .5 seconds...", 0)
                try:
                    f = urllib.request.urlopen(url)
                    pprint("Second request successful, reading data...")
                    bibtex = f.read().decode('utf-8')
                except:
                    pprint("Paper with id {} not found even after waiting.".format(query), 0)
                    raise cls.PaperNotFound
                else:
                    return bibtex
            else:
                pprint("Paper with id {} not found. HTTP response: {}".format(query, err.reason), 0)
                raise cls.PaperNotFound
        else:
            if bibtex:
                return bibtex
            else:
                pprint("Query with inspre label {} produced no result".format(query), 0)
                raise cls.PaperNotFound


    @classmethod
    def get_page(cls, arxiv_no=None, inspire_id=None, verbose=1):
        """Given the arxiv number of a paper or the bibtex identifier return the internal record identifier"""

        def pprint(arg, verbosity=1):
            # Prints only if the argument verbose of get is bigger than the verbosity of the message
            if verbose > verbosity:
                print(arg)

        recid = None

        if arxiv_no:
            request_arxiv = f'literature/?q={arxiv_no}&format=json'.replace(' ', '%20')
            url = APIURL + request_arxiv

            pprint("Now requesting...")
            try:
                f = urllib.request.urlopen(url)
                pprint("Request successful, reading data...")
                recid = json.load(f)['hits']['hits'][0]['id']
            except urllib.error.HTTPError as err:
                pprint("Paper with eprint {} not found. Trying with inspire ID".format(arxiv_no), 0)
                pass
            except (KeyError, IndexError):
                pprint("Paper with eprint {} not found. Trying with inspire ID".format(arxiv_no), 0)
                pass

        if inspire_id:
            request_inspire = f'literature/?q={inspire_id}&format=json'
            url = APIURL + request_inspire

            pprint("Now requesting...")
            try:
                f = urllib.request.urlopen(url)
                pprint("Request successful, reading data...")
                recid = json.load(f)['hits']['hits'][0]['id']
            except urllib.error.HTTPError as err:
                pprint("Paper with Inspire ID {} not found.".format(inspire_id), 0)
                raise cls.PaperNotFound
            except (KeyError, IndexError):
                pprint("Paper with Inspire ID {} not found.".format(inspire_id), 0)
                raise cls.PaperNotFound

        if recid:
            return f"https://inspirehep.net/literature/{recid}"
        elif inspire_id is None and arxiv_no is None:
            raise ValueError("Either Arxiv number or Inspire ID must be given")
        else:
            raise cls.PaperNotFound


    def list_papers(self, category, verbose, done_method, done_method_next = None):
        """Gets the new paper from the file .arxiv_new.txt if exists"""
        if done_method_next is None:
            done_method_next = done_method
        filepath = os.path.join(os.path.expanduser('~/.cache/bibmanager'), '.arxiv_new.txt')
        if os.path.isfile(filepath):
            with open(filepath,'r') as f:
                try:
                    content = eval(f.read())
                except SyntaxError:
                    print("The file with the new papers was corrupted, fetching them again.")
                    self.save_paperlist(category, verbose, self.list_papers, category, verbose, done_method_next)
                    return

            if content["category"] == category and date.fromisoformat(content["date"]) == date.today():
                self.contents = content["papers"]
                done_method(self)
                return

        print('File with new papers not available, I am loading them now...')
        self.save_paperlist(category, verbose, self.list_papers, category, verbose, done_method_next)

    @classmethod
    def save_paperlist(cls, category, verbose, function, *args):
        """Saves a file .arxiv_new.txt with the new papers"""
        content = {"category": category, "date":date.today().isoformat()}

        def done():
            results = cls.fetch_papers(category, verbose)
            content["papers"] = results
            folderpath = os.path.expanduser('~/.cache/bibmanager')
            if not os.path.isdir(folderpath):
                os.makedirs(folderpath)
            filepath = os.path.join(folderpath, '.arxiv_new.txt')
            with open(filepath, 'w+') as f:
                f.write(str(content))
            time.sleep(.1)
            function(*args)

        proc = threading.Thread(target=done)
        proc.start()

    @classmethod
    def fetch_papers(cls, category, verbose = 1):
        """Lists the paper id's and titles in the Arxiv/new section of the day"""
        def pprint(arg, verbosity = 1):
            #Prints only if the argument verbose of get is bigger than the verbosity of the message
            if verbose > verbosity:
                print(arg)

        #This looks for the paper id's in the arxiv/new section
        def Xpath(m, n):
            return f'//*[@id="dlpage"]/dl[{m}]/dt[{n}]/span/a[1]'
        pprint("Now requesting from {}/new...".format(category))
        url = ARXIVURL.format(category)
        f = urllib.request.urlopen(url)
        pprint("Request successful, reading data...")
        data = f.read()
        pprint("Data read, parsing data...")
        html = lxml.html.fromstring(data)
        
        results = []
        ind = 1
        for a in [1,2]:
            leng = ind-1
            ind = 1
            lis = html.xpath(Xpath(a, ind))
            while lis != []:
                results.append(lis[0].text.replace("arXiv:",""))
                ind += 1
                lis = html.xpath(Xpath(a, ind))

        if results == []:
            pprint("No papers found.", 0)
        else:
            for r in results:
                pprint(r)
        pprint("Parsing successful.")

        #This makes a request to the API to get the titles as well
        #In the arxiv/new page they are mixed with MathJax.
        url = ARXIVAPI + "query?id_list="  + ",".join(results) + "&start=0&max_results=100"

        pprint("Now requesting titles from the API...")
        f = urllib.request.urlopen(url)
        pprint("Request successful, reading data...")
        data = f.read()
        pprint("Data read, parsing data...")
        xml = lxml.etree.fromstring(data)
        titles = [b.text.replace("\n","") for b in xml.iterfind(".//{*}title")][1:]

        results = results[:leng] + [""] + results[leng :]
        titles = titles[:leng] + ["————Cross-lists————"] + titles[leng:]
        #This zips together {arxiv_id:title, ... }
        results = dict(zip(results, titles))

        return results

    class PaperNotFound(Exception):
        pass
