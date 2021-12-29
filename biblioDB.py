import re

"""
self.entries is a dictionary of Bibentry instances. The keys are the inspire id's.
The values belong the the class Bibentry and have their own attributes.
self.comment_entries is a dictionary of dictionaries. The keys are the inspire id's.
The values are dictionaries {"description": <string>, "category": <string>, "local_pdf": <string>}
"""

"""
To do: make it so that the search ignores accents and diacritics
"""


class Biblio:
    diacritics = {"\\'e":'é','\\"a': 'ä', '\\"o': 'ö', '\\~n': 'ñ', "\\'c": 'ć', '\\u g':'ğ', '\\v c': 'č',"\\'o": 'ò', '\\L':'Ł', '\\_':'_', '\c{c}':'ç', '\\"u':'ü', '\\"U':'Ü', '\\`a':'à'}
    
    def __init__(self):
        self.entries = {}
        self.comment_entries = {}
        self.parse("")

    def parse(self, contents):
        """Parses an input from a .bib file."""
        self.raw_entries = []

        found_cat_dict = re.search("^%{(.*:.*)*}", contents, flags = re.MULTILINE)
        if found_cat_dict:
            self.cat_dict = eval(found_cat_dict.group(0)[1:])
        else:
            self.cat_dict = {"":"All","r":"To read"}

        contents_no_comments = re.sub("^%(.*?)\n","",contents, flags = re.MULTILINE)

        matchAt = list(re.finditer("@([A-z]+?){", contents_no_comments))
        nmatches = len(matchAt)
        for p in range(nmatches):
            raw_entry = contents_no_comments[matchAt[p].start(0): matchAt[p+1].start(0) if p < nmatches - 1 else None]
            self.raw_entries.append(raw_entry.strip("\n "))

        #Parse each @xxxx{ ... } entry
        for r in self.raw_entries:
            self.parse_raw_entry(r)

        #Now we link the comment lines to the bib entries
        for e in self.entries.values():
            self.link_comment_entry(e)

        #Finally we remove the categories that did not show up in the flags
        all_flags = ""
        for e in self.entries.values():
            for c in e.flags:
                if not c in all_flags:
                    all_flags += c

        for l in list(self.cat_dict.keys()):
            if not l in all_flags:
                del(self.cat_dict[l])

    def parse_raw_entry(self, r, not_a_comment = False):
        """Parses a single @xxxx{ ... } entry and also returns the inspire_id."""
        id_match = re.search("@([A-z].+?){(.+?),", r)
        if id_match is None:
            if not_a_comment:
                raise self.ParseError("Missing inspire_id in\n" + r)
            elif re.search("@COMMENT{", r):
                self.comment_entries = self.parse_comments(r.replace("@COMMENT", "").strip("\n{} "))
            else:
                raise self.ParseError("Comment header not valid\n" + r.split("\n")[0])
        else:
            def remove_many_spaces(string):
                temp_string = string
                new_string = ""
                while temp_string != new_string:
                    new_string = temp_string
                    temp_string = new_string.replace("  "," ")
                return temp_string
    
            found_inspire_id = id_match.group(2)
            #Match title
            title_match = re.search("title([ \t]*)=([ \t]*)(\"|{)", r, re.I)
            if title_match:
                found_title = self.parse_element(title_match.group(3), title_match.start(3), r)
                found_title = found_title.replace("\n"," ").replace("\t","")
                found_title = remove_many_spaces(found_title)
                if found_title[0] == "{":
                    found_title = found_title[1:-1]
            else:
                print("Title not found in\n" + r)
                found_title = "not found"
            #Match ArXiv number
            arxiv_match = re.search("eprint([ \t]*)=([ \t]*)(\"|{)(.+?)(\"|})\s*(,|(}\s*$))", r, re.I)
            if arxiv_match:
                found_arxiv = arxiv_match.group(4)
            else:
                found_arxiv = "n/a"
            #Match authors
            author_match = re.search("author([ \t]*)=([ \t]*)(\"|{)", r, re.I)
            if author_match:
                author_group = self.parse_element(author_match.group(3), author_match.start(3), r)
                author_group = author_group.replace("\n"," ").replace("\t","")
                author_group = remove_many_spaces(author_group)
                found_authors, found_initials = self.process_authors(author_group)
            else:
                print("Authors not found in\n" + r)
                found_authors, found_initials = ([("not","found")],"")

            #Check that the whole string will compile on BibTex
            self.check_all(r)

            #Finally save the entry
            en = Bibentry(title = found_title,
                        arxiv_no = found_arxiv,
                        inspire_id = found_inspire_id,
                        bibentry = r,
                        authors = found_authors,
                        initials = found_initials)
            self.entries.update({found_inspire_id:en})

            return found_inspire_id

    def link_comment_entry(self, e):
        """Links the content of the comment section to the description of the entry"""
        e.description = self.comment_entries.get(e.inspire_id, {"description":"Not found"})["description"]
        e.flags = self.comment_entries.get(e.inspire_id, {"category":""})["category"]
        e.local_pdf = self.comment_entries.get(e.inspire_id, {"local_pdf":""})["local_pdf"]

    @classmethod
    def get_id(cls, text):
        """Gets the inspire id of a text"""
        id_match = re.search("@([A-z].+?){(.+?),", text)
        if id_match:
            return id_match.group(2)
        else:
            raise cls.ParseError("Comment header not valid\n" + text.split("\n")[0])


    class ParseError(Exception):
        """An error occurred when parsing the contents of the file."""
        def __init__(self, error = ""):
            print(error)

    def check_all(self, string):
        """Checks that the whole string compiles in BibTex"""
        def escape_count(source, st):
            """Counts the occurrences of the st in source excluding those that are escaped, i.e. \st"""
            found = re.findall(r"(?<!\\)" + st, source)
            return len(found)
        string_nocomment = re.sub("^%(.*?)\n", "", string, flags = re.MULTILINE)
        entry_ok = re.match('\s*@(.+?){([^"{},]+?),(.*)(,?\s*)}\s*$', string_nocomment, re.DOTALL)
        if entry_ok:
            args = entry_ok.group(3)
            if escape_count(args, "{") == escape_count(args, "}"):
                commas = [-1]
                listenquote = True
                listenbrace = 0
                escaped = False
                for i, c in enumerate(args):
                    if not escaped:
                        if c == "\\":
                            escaped = True
                        elif c == '"' and listenbrace == 0:
                            listenquote = not listenquote
                        elif c == "{":
                            listenbrace += 1
                        elif c == "}":
                            listenbrace -= 1
                        elif listenquote and listenbrace == 0:
                            if c == ",":
                                commas.append(i)
                    else:
                        escaped = False
                if listenquote is False:
                    raise self.ParseError('This entry will not compile on BibTex. Unbalanced "" in\n' + args)
                strings = []
                commas.append(None)
                for i, comma in enumerate(commas[:-1]):
                    strings.append(args[comma+1:commas[i+1]])
                for s in strings:
                    mat = re.match('(\s*([\w\-.]+)\s*=\s*((".*")|({.*})|(\w+))\s*)|\s*$', s, re.DOTALL)
                    if mat is None:
                        raise self.ParseError("This line in the entry will not compile on BibTex\n" + s)
                return True
            else:
                raise self.ParseError('This entry will not compile on BibTex. Unbalanced {} in\n' + args)
        else:
            raise self.ParseError("This entry will not compile on BibTex\n" + string)


    def parse_element(self, quotes_or_braces, start, text):
        """Parses an element from <field> = "..." or <field> = {...}"""
        def common_replacements(string):
            """Some replacements, mostly for diacritics and accents"""
            final = string
            for tex, char in self.diacritics.items():
                final = final.replace(tex, char)
            return final
        #This works even if the element spreads across different lines
        status = 1
        escape = False
        token_up = "{" if quotes_or_braces == "{" else "\""
        token_down = "}" if quotes_or_braces == "{" else "\""
        for pos, chars in enumerate(text[start+1:]):
            if escape:
                escape = False
            elif status == 0:
                return common_replacements(text[start+1:start+pos])
            else:
                if chars == '\\':
                    escape = True
                if chars == token_down:
                    status -= 1
                elif chars == token_up:
                    status += 1

        return common_replacements(text[start+1:])
            
    def process_authors(self, string):
        """Processes the name by splitting the "and" and by organizing name and last name in tuples
        supports both the format "Name Last Name" (possibly with {}) and "Last Name, Name"."""
        def process_name(string):
            temp = string.replace("{","").replace("}","").split(",")
            if len(temp) != 2:
                #Special rule when the author names are not separated by a comma
                s = ""
                nstring = string
                nstring_temp = ""
                #This replaces spaces in brackets by _ to keep the words together. Then I put the spaces back.
                while nstring_temp != nstring:
                    nstring_temp = nstring
                    nstring = re.sub("{([^}]*)( +)([^}]*)}","{\g<1>_\g<3>}",nstring)
                nstring = nstring.replace("}","").replace("{","").strip(" ")
                for a in nstring.split(" ")[1:]:
                    s = s+a+" "
                temp = [s[0:] , nstring.split(" ")[0]]
            for t in range(2):
                temp[t] = temp[t].replace("_"," ").strip(" ")
            return temp

        initials = ""
        authors_list = []
        listen = True
        and_string = ""
        record = 0
        current = 0
        #This is a lexer that recognizes the token and surrounded by spaces when it's not inside braces {}.
        for ch in string:
            current += 1
            if ch == "{":
                listen = False
            elif ch == "}":
                listen = True
                and_string = ""
            elif listen:
                if (and_string == "" and ch == " ") or (and_string == "" and ch == "\n"):
                    and_string = " "
                if (and_string == " " and ch == " ") or (and_string == " " and ch == "\n"):
                    and_string = " "
                elif and_string == " " and ch == "a":
                    and_string = " a"
                elif and_string == " a" and ch == "n":
                    and_string = " an"
                elif and_string == " an" and ch == "d":
                    and_string = " and"
                elif (and_string == " and" and ch == " ") or (and_string == " and" and ch == "\n"):
                    and_string = " and "
                    lastname, name = process_name(string[record:current-5])
                    authors_list.append((name, lastname))
                    initials += lastname[0:2]
                    record = current
                    and_string = ""
                else:
                    and_string = ""
        lastname, name = process_name(string[record:])
        authors_list.append((name, lastname))
        initials += lastname[0:2 if len(authors_list) > 1 else 3]
        if len(authors_list) > 3:
            initials = initials[0:-1:2]

        return (authors_list, initials)

    def parse_comments(self, string):
        """Parses the first @COMMENT entry containing all the paper descriptions"""
        splitted = string.split("\n")
        final = {}
        for s in splitted:
            t = s.split("|")
            if len(t) < 4:
                t = t + ["" for i in range(4-len(t))]
            inspire_id = t[0].strip(" \t")
            d = {"description": t[1].strip(" \t"), "category": t[2].strip(" \t"), "local_pdf": t[3].strip(" \t")}
            final.update({inspire_id:d})

        return final

    def comment_string(self):
        """Writes the whole string enclosed in @COMMENT. To be used for saving on file"""
        string = "%" + str(self.cat_dict) + "\n\n@COMMENT{\n"
        for key, entry in self.comment_entries.items():
            string += "{} | {} | {} | {}\n".format(key, entry["description"], entry["category"], entry["local_pdf"])
        return string + "}\n\n"

    def parse_search(self, string):
        """Parses a search string and returns a dictionary {"author":..., "title":..., "description":..., "all":...}
        "author" takes all words preceded by a, "title" by t, "description" by d, "arxiv" by n, "all" by nothing.
        Consecutive words are grouped using quotes"""
        listen = True
        marks = [-1]
        for i,c in enumerate(string):
            if listen:
                if c == " ":
                    marks.append(i)
                elif c == "\"":
                    listen = not listen
            else:
                if c == "\"":
                    listen = not listen
        splitted = []
        marks.append(None)
        for i, mark in enumerate(marks[1:]):
            splitted.append(string[marks[i]+1: mark])
        splitted = [a.strip("\"") for a in splitted if a is not ""]

        splitted = iter(splitted)
        search_query = []
        for s in splitted:
            if s in ["a", "d", "t", "n"]:
                try:
                    search_query.append((s,next(splitted)))
                except StopIteration:
                    search_query.append(("all",s))
            else:
                search_query.append(("all",s))

        search_query = {"author":      [x[1] for x in search_query if x[0] == "a"],
                        "title":       [x[1] for x in search_query if x[0] == "t"],
                        "description": [x[1] for x in search_query if x[0] == "d"],
                        "arxiv":       [x[1] for x in search_query if x[0] == "n"],
                        "all":         [x[1] for x in search_query if x[0] == "all"]}

        return search_query

    def filter(self, query):
        """Filters bibliography entries (turning them invisible) according to the query specified"""
        def flatten(lis):
            flat = ""
            for a in lis:
                flat += "{} {} ".format(*a)
            return flat
        def does_it_match(entry):
            for n in query["arxiv"]:
                match = re.search(n, entry.arxiv_no)
                if not match:
                    return False
            for auth in query["author"]:
                match = re.search(auth, flatten(entry.authors), re.IGNORECASE)
                if not match:
                    return False
            for titl in query["title"]:
                match = re.search(titl, entry.title, re.IGNORECASE)
                if not match:
                    return False
            for desc in query["description"]:
                match = re.search(desc, entry.description, re.IGNORECASE)
                if not match:
                    return False
            for a in query["all"]:
                match1 = re.search(a, entry.title, re.IGNORECASE)
                match2 = re.search(a, flatten(entry.authors), re.IGNORECASE)
                match3 = re.search(a, entry.description, re.IGNORECASE)
                match4 = re.search(a, entry.arxiv_no)                
                if not (match1 or match2 or match3 or match4):
                    return False
            return True
                
        for key, entry in self.entries.items():
            try:
                is_match = does_it_match(entry)
            except:
                print("Regular expression invalid.")
                return None
            if is_match:
                entry.visible = True
            else:
                entry.visible = False

    def sort_by(self, key):
        """Sorts the entries of the dictionary according to the key key."""
        #Careful: this implementation works only on Python 3.6+ because it relies on the fact
        #that dictionaries keep the order in which they are created!
        sorted_entries = sorted(self.entries.items(), key = lambda x: key(x[1]))
        self.entries = dict(sorted_entries)
            


class Bibentry():
    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            self.__setattr__(key, val)
        self.visible     = True
        self.date        = self.compute_date()

    def compute_date(self):
        """Computes the date in months from 1 Jan 1900. If there is an arxiv number of the form yymm.xxxx uses that
           otherwise looks in bibentry and if nothing works returns just zero"""
        found_arxiv = re.match("([0-9]{4,4})\.([0-9]+)",self.arxiv_no)
        if found_arxiv:
            yymm = found_arxiv.group(1)
            index = float("0." + found_arxiv.group(2))
            return 12*int("1" + yymm[0:2]) + int(yymm[2:4]) - 1 + index
        else:
            found_year = re.search("year([ \t]*)=([ \t]*)(\"|{)?([0-9]{4,4})(\"|})?", self.bibentry)
            if found_year:
                return (int(found_year.group(4)) - 1900)*12
            else:
                return 0

    def write(self):
        """Writes the entry bibentry. To be used for saving on file"""
        return self.bibentry + "\n\n"

    def copy(self):
        """Copies the instance"""
        return Bibentry(title = self.title,
                        arxiv_no = self.arxiv_no,
                        inspire_id = self.inspire_id,
                        bibentry = self.bibentry,
                        authors = self.authors.copy(),
                        initials = self.initials)


