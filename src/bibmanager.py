#!/usr/bin/env python3

from tkinter import *
from biblioGUI import *
import sys,os

def main():
    """Main function"""
    dir_path = os.path.dirname(os.path.realpath(__file__))

    overwrite_flags     = True
    ini_def_cat         = "hep-th"
    ini_path            = dir_path + "/biblio.bib"
    linked_pdf_relative = True
    default_pdf_path    = dir_path
    pdf_viewer          = ("zathura", "zathura")
    request_verbosity   = 1
    def_term		= 'gnome-terminal --'

    #Reads the config file if it exists
    try:
        with open(os.path.expanduser('~/.config/bibmanager/bibmanager.config')) as file:
            for l in file.readlines():
                if l[0] != "#" and l != "\n":
                    equals = l.index("=")+1
                    key, val = l[:equals-1], l[equals:-1]
                    key = key.strip()
                    val = val.strip("\n ")
                    if key == 'default_file':
                        if os.path.isabs(val):
                            ini_path = os.path.expanduser(val)
                        else:
                            ini_path = dir_path + "/" + val
                    elif key == 'overwrite_flags':
                        overwrite_flags = eval(val.capitalize())
                    elif key == 'default_category':
                        ini_def_cat = val
                    elif key == 'default_pdf_path':
                        if os.path.isabs(val):
                            default_pdf_path = os.path.expanduser(val)
                        else:
                            default_pdf_path = dir_path + "/" + val
                    elif key == 'pdf_viewer':
                        spl = val.split(",")
                        if len(spl) == 1:
                            pdf_viewer = (spl[0].strip(" "), spl[0].strip(" "))
                        else:
                            pdf_viewer = (spl[0].strip(" "), spl[1].strip(" "))
                    elif key == 'linked_pdf_relative':
                        linked_pdf_relative = eval(val.capitalize())
                    elif key == 'default_terminal':
                        def_term = val.strip("'\"")
    except:
        pass

    #Takes the file from the first argument, otherwise loads a default one
    default_filename = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else ini_path

    master = Tk()
    biblio = Biblio()
    root   = Root(master, biblio, *sys.argv,
                  default_filename    = default_filename,
                  ini_def_cat         = ini_def_cat,
                  overwrite_flags     = overwrite_flags,
                  linked_pdf_relative = linked_pdf_relative,
                  default_pdf_path    = default_pdf_path,
                  pdf_viewer          = pdf_viewer,
                  request_verbosity   = request_verbosity,
                  default_terminal    = def_term)

    master.mainloop()

if __name__ == "__main__":
    main()
