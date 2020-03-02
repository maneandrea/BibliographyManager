#!/usr/bin/env python3

from tkinter import *
from biblioGUI import *
import sys,os

def main():
    """Main function"""
    dir_path = os.path.dirname(os.path.realpath(__file__))

    overwrite_flags = True
    ini_def_cat = "hep-th"
    ini_path = dir_path + "/../../PhD/LaTeX/Bibliography/biblio.bib"

    #Reads the config file if it exists
    try:
        with open('bibconfig') as file:
            for l in file.readlines():
                if l[0] != "#" and l != "\n":
                    equals = l.index("=")+1
                    key, val = l[:equals-1], l[equals:-1]
                    key = key.strip()
                    val = val.strip("\n ")
                    if key == 'default_file':
                        if os.path.isabs(val):
                            ini_path = val
                        else:
                            ini_path = dir_path + "/" + val
                    elif key == 'overwrite_flags':
                        overwrite_flags = eval(val.capitalize())
                    elif key == 'default_category':
                        ini_def_cat = val
    except:
        pass

    #Takes the file from the first argument, otherwise loads a default one
    default_filename = sys.argv[1] if len(sys.argv) > 1 else ini_path

    master = Tk()
    biblio = Biblio()
    root   = Root(master, biblio, default_filename, ini_def_cat, overwrite_flags, *sys.argv)

    master.mainloop()

if __name__ == "__main__":
    main()
