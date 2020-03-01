#!/usr/bin/python3
import urllib
from urllib.request import urlopen
import lxml.html

APIURL = "http://inspirehep.net/search?"
ARXIVURL = "https://arxiv.org/list/{}/new"
ARXIVAPI = "http://export.arxiv.org/api/"

class Query:
    def __init__(self):
        pass

    @classmethod
    def get(cls, arxiv_no, verbose = 1):
        """Given the arxiv number of a paper requests the Bibtex entry to Inspire's API"""
        def pprint(arg, verbosity = 1):
            #Prints only if the argument verbose of get is bigger than the verbosity of the message
            if verbose > verbosity:
                print(arg)

        request = "p={}&of={}&jrec={}&".format(
            "find+eprint+" + arxiv_no.strip(" "),
            "hx",
            "001")
        Xpath = "/html/body/div[2]/div/pre/text()"
        url = APIURL + request

        pprint("Now requesting...")
        f = urlopen(url)
        pprint("Request successful, reading data...")
        data = f.read()
        pprint("Data read, parsing data...")
        html = lxml.html.fromstring(data)
        bibtex = html.xpath(Xpath)
        pprint("Parsing successful.")
        
        if len(bibtex) > 0:
            return bibtex[0].strip("\n ")
        else:
            pprint("Paper with eprint {} not found.".format(arxiv_no), 0)
            raise cls.PaperNotFound
            return ""

    @classmethod
    def list_papers(cls, category, verbose = 1):
        """Lists the paper id's and titles in the Arxiv/new section of the day"""
        def pprint(arg, verbosity = 1):
            #Prints only if the argument verbose of get is bigger than the verbosity of the message
            if verbose > verbosity:
                print(arg)

        #This looks for the paper id's in the arxiv/new section
        def Xpath(m, n):
            return f'//*[@id="dlpage"]/dl[{m}]/dt[{n}]/span/a[1]'
        pprint("Now requesting from hep-th/new...")
        url = ARXIVURL.format(category)
        f = urlopen(url)
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
        f = urlopen(url)
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
