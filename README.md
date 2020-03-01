Bibliography Manager
---

This is a tool for managing a BibTeX bibliography file and to sort and order papers. It is mainly thought for high energy physics as it works together with Inspire and ArXiv API.   

It is written in Python 3 and uses the libraries

- tkinter (for the GUI)
- re (for parsing .bib files)
- webbrowser (for opening paper pdfs)
- urllib, lxml (for making http requests to Inspire and ArXiv)
- PIL, sympy (for rendering LaTeX)

It can read and save files in a .bib format. Additional information needed for this application is saved within the .bib file in the form of a comment string.

Every paper is associated to a unique ID (typically the Inspire ID) and is given a small description. Data can be automatically retrieved from the Inspire database. It is also possible to add papers from the present day directly from within the application.

The application offers a way to categorize papers in up to 26 customizable "groups". Any paper can belong to zero or more groups. Paper can then be searched for keywords or filtered by groups.

Furthermore it is possible to select a subset of papers and create a new .bib file containing only those. This is useful for creating paper specific bibliographies to share with coauthors.