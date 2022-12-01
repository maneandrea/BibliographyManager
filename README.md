Bibliography Manager
---

This is a tool for managing a BibTeX bibliography file and to sort and order papers. It is mainly thought for high energy physics as it works together with Inspire and ArXiv API.   

### Main structure

 - It reads and saves files in a .bib format. Additional information needed for this application is saved within the .bib file in the form of a comment string.

 - Every paper is associated to a unique ID (typically the Inspire ID) and is given a small description.

 - Papers can be categorized in "groups". Any paper can belong to zero or more groups. Papers can then be searched for keywords or filtered by groups.

 - Some global parameters of the application can be chosen by editing the (documented) bibconfig file.

### Features

#### Local management

 - It is possible to select a subset of papers and create a new .bib file containing only those. This is useful for creating paper specific bibliographies to share with coauthors. It is also possible to export only the needed papers by reading from a .bbl file.

 - One can save locally the pdf documents of the papers and link them to the entry in the database. If a local copy is available, that one will be opened instead of the online pdf from Arxiv. The paths are stored within the .bib file. They can be chosen as absolute (if one plans to move the .bib file around) or relative (if one has the .bib file in e.g. a Dropbox folder across multiple computers).

#### Interactions with Inspire

 - The bibtex entry of a paper and various metadata can be downloaded automatically from Inspire. For this, it is sufficient to provide the ArXiv identifier or the Inspire id. It is also possible to add papers from the present day directly from within the application.

 - It is possible to fetch updates for one or more papers and also to fetch updates only for the papers that only have the preprint information (in case they have been published in the meantime).

 - It is possible to read a .bbl file and automatically import from Inspire all papers contained in it. This assumes that the paper identifiers match the default identifiers on Inspire.

 - There are shortcuts to open the Arxiv abstract page, the Inspire page, the author page and the pdf of a given paper.

---

This program is distributed under the terms of the GNU General Public License,
version 3 or later. See the file [LICENSE](LICENSE) for details.
