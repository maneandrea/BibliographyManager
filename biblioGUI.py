#!/usr/bin/python3

from tkinter import *
from tkinter import messagebox, filedialog, simpledialog, font
import webbrowser
import os, sys, time

#My packages
from otherWidgets import *      #Some functionalities are compatible with TkTreectrl
from biblioDB import *
from inspireQuery import *

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
                    overwrite_flags = eval(val)
                elif key == 'default_category':
                    ini_def_cat = val
except:
    pass
    

#Takes the file from the first argument, otherwise loads a default one
default_filename = sys.argv[1] if len(sys.argv) > 1 else ini_path
icon = "Icons/icon.png"

"""
This determines whether to overwrite or add new flags when multiple papers are selected.
I haven't yet decided what behavior I want it to have
"""

class Root:
    """This is the main window"""
    def __init__(self, master, bibliography):
        #The Biblio object with which we interact
        self.biblio = bibliography

        #For Save / Save As
        self.current_file = default_filename
        self.is_modified = False

        #Asks the Arxiv number right after pressing Add
        self.ask_arxiv_on_add = True
        
        #Window config
        self.master = master
        master.protocol("WM_DELETE_WINDOW", self.on_close)
        master.call('wm', 'iconphoto', master._w, PhotoImage(file = icon))
        master.title("Bibliography - " + default_filename.split("/")[-1])
        self.paned = PanedWindow(master)
        self.paned.config(sashrelief = RAISED, sashwidth = 8)
        ini_halfwidth = 600
        ini_height = 600

        #Left and right panels
        self.frame_left = Frame(self.paned)
        self.frame_right = Frame(self.paned)
        self.frame_left.config( width = ini_halfwidth, height = ini_height)
        self.frame_right.config(width = ini_halfwidth, height = ini_height)
        masterl = self.frame_left
        masterr = self.frame_right
        self.paned.add(masterl)
        self.paned.add(masterr)
        self.paned.pack(fill=BOTH, expand=1)

        #Define fonts
        self.listfont = font.Font(family="DejaVu Sans", size=12)
        self.columnfont = font.Font(family="DejaVu Sans", size=12, slant="italic")
        LMSS = "Calibri" if os.name == "nt" else "Latin Modern Sans"
        self.titlefont = font.Font(family=LMSS, size=20, weight="bold")
        self.authorsfont = font.Font(family=LMSS, size=16)
        DEJAVUSANSMONO = "Lucida Sans Typewriter" if os.name == "nt" else "DejaVu Sans Mono"
        self.bibentryfont = font.Font(family=DEJAVUSANSMONO, size=13)

        #MultiListbox config
        self.paper_list = MultiListbox(masterl)
        self.paper_list.config(columns = ("Inspire ID", "Authors", "Description"), font = self.listfont,
                               selectcmd = self.list_has_changed, columnfont = self.columnfont)
        #This fixes the initial widths of the columns
        self.paper_list.set_widths(100, 80)
        #This binds Sort by Date to the first column and Sort by Title to the Last
        self.paper_list.bind_command("Inspire ID", self.on_sort_date)
        self.paper_list.bind_command("Description", self.on_sort_title)
        #This adds the tooltips
        self.tooltip_datesort  = CreateToolTip(master, self.paper_list.column_dict["Inspire ID"].top, text = "Sort by date (Not Inspire ID)")
        self.tooltip_titlesort = CreateToolTip(master, self.paper_list.column_dict["Description"].top, text = "Sort by title (Not description)")


        #Title config: LatexText is a widget based on text that is able to render LaTeX
        self.paper_title = LatexText(masterr)
        self.paper_title.config(font = self.titlefont, state = DISABLED,
                                height = 1, bg = masterr.cget('bg'), relief = FLAT, wrap = WORD)
        self.paper_title.bindtags((str(self.paper_title), str(masterr), "all"))

        #Authors config: HyperrefText is a widget based on Text that is able to contain hypertext
        self.paper_authors = HyperrefText(masterr)
        self.paper_authors.config(font = self.authorsfont, state = DISABLED,
                                  height = 1, bg = masterr.cget('bg'), relief = FLAT, wrap = WORD, cursor = "arrow")
        self.paper_authors.bindtags((str(self.paper_authors), str(masterr), "all"))

        #Text box
        self.bibentry = Text(masterr)
        self.bibentry.config(font = self.bibentryfont)
        #This will represent the binding to <1> that removes the info message on the bibentry that appears after doing "Add"
        self.bibentry.binding = None

        #Right-click menu for the textbox
        self.popup_menu = Menu(self.master, tearoff=0, postcommand = self.enable_menu)
        self.popup_menu.add_command(label="Cut",
                                    command = self.on_cut, state = DISABLED)
        self.popup_menu.add_command(label="Copy",
                                    command = self.on_copy, state = DISABLED)
        self.popup_menu.add_command(label="Paste",
                                    command = self.on_paste)
        self.popup_menu.add_separator()
        self.popup_menu.add_command(label="Indent",
                                    command = self.on_indent, state = DISABLED)
        self.popup_menu.add_command(label="De-indent",
                                    command = self.on_deindent, state = DISABLED)
        self.bibentry.bind("<Button-3>", self.right_click_popup)
        self.popup_menu.bind("<Leave>", self.exit_popup)
        
        #Label with inspire id
        self.inspire_text = StringVar()
        self.inspire_id = Entry(masterr)
        self.inspire_id.config(state = "readonly", textvariable = self.inspire_text,
                               font = self.listfont, relief = FLAT, bg = master.cget("bg"))
        self.inspire_id.bind("<Double-Button-1>", self.copy_to_clipboard)

        #Buttons with links to the ArXiv
        self.arxiv_link = StringVar()
        self.arxiv_abs = Button(masterr)
        self.arxiv_pdf = Button(masterr)
        self.arxiv_abs.config(textvariable = self.arxiv_link, font = self.listfont, command = self.on_arxiv_abs())
        self.arxiv_pdf.config(text = "PDF", font = self.listfont, command = self.on_arxiv_pdf())

        #Button that gets the bibtex text from Inspire
        self.get_bibtex = Button(masterr)
        self.get_bibtex.config(text = "Get Bibtex", font = self.listfont, command = self.on_get_bibtex, state = DISABLED)

        #Text box to edit the paper comments
        self.comment = StringVar()
        self.text_box = Entry(masterr)
        self.text_box.config(font = self.listfont, textvariable = self.comment)
                
        #Button for updating the new data
        self.update_paper = Button(masterr)
        self.update_paper.config(text = "Update", font = self.listfont, command = self.on_update, state = DISABLED)

        #Buttons for deleting and adding
        self.add_paper = Button(masterl)
        self.select_all = Button(masterl)
        self.add_paper.config(text = "Add", font = self.listfont, command = self.on_add)
        self.add_paper.bind("<3>", self.toggle_arxiv_add)
        self.select_all.config(text = "Select All", font = self.listfont, command = self.on_select_all)

        #Textbox and button for searching
        self.search_button = Button(masterl)
        self.search_button.config(text = "Search", font = self.listfont, command = self.on_search)
        self.search_string = StringVar()
        self.search_box = Entry(masterl)
        self.search_box.config(textvariable = self.search_string, font = self.listfont)
        self.search_box.bind("<Return>", self.on_search)
        self.search_box.bind("<Escape>", self.on_exit_search)
        self.tooltip = CreateToolTip(master, self.search_box, text = "Prepend a to search by author, t by title, d by description, "
                                     "n by ArXiv number and nothing by all.\nGroup words with quotes. The search ignores cases.")

        #Status bar
        self.status_bar = Label(masterr)
        self.status = StringVar()
        self.status_bar.config(textvariable = self.status, font = self.listfont, anchor = W, relief = SUNKEN,
                               justify = LEFT, height = 1)

        #Variables for the arxiv category
        self.def_cat = StringVar()
        self.def_cat.set(ini_def_cat)

        #Menu
        self.menu = Menu(master, font = self.listfont)
        self.filemenu = Menu(self.menu, tearoff = 0, font = self.listfont)
        self.filemenu.add_command(label = "New...                     Ctrl+N", command = self.on_new_file)
        self.filemenu.add_command(label = "Open...                    Ctrl+O", command = self.on_open_file)
        self.filemenu.add_command(label = "Open and merge... Ctrl+Shift+O", command = self.on_open_file_merge)
        self.filemenu.add_separator()
        self.filemenu.add_command(label = "Save...                     Ctrl+S", command = self.on_save_this_file)
        self.filemenu.add_command(label = "Save As...                Ctrl+Shift+S", command = self.on_save_file)
        self.filemenu.add_separator()
        self.export = Menu(self.filemenu, tearoff = 0, font = self.listfont)
        self.filemenu.add_cascade(label = "Export...", menu = self.export)
        self.export.add_command(label = "Selected        Ctrl+E", command = self.export_selected)
        self.export.add_separator()
        self.filemenu.add_separator()
        self.filemenu.add_command(label = "Exit                          Ctrl+Q", command = self.on_close)
        self.menu.add_cascade(label = "File", menu = self.filemenu)
        self.editmenu = Menu(self.menu, tearoff = 0, font = self.listfont)
        self.editmenu.add_command(label = "Add", command = self.on_add)
        self.editmenu.add_command(label = "Remove", command = self.on_remove)
        self.editmenu.add_command(label = "Update", command = self.on_update)
        self.editmenu.add_command(label = "Get Bibtex", command = self.on_get_bibtex)
        self.catmenu = Menu(self.editmenu, tearoff = 0, font = self.listfont)
        self.catmenu.add_radiobutton(label = "hep-th", variable = self.def_cat, value = "hep-th")
        self.catmenu.add_radiobutton(label = "hep-ph", variable = self.def_cat, value = "hep-ph")
        self.catmenu.add_radiobutton(label = "hep-lat", variable = self.def_cat, value = "hep-lat")
        self.catmenu.add_radiobutton(label = "math-ph", variable = self.def_cat, value = "math-ph")
        self.catmenu.add_radiobutton(label = "gr-qc", variable = self.def_cat, value = "gr-qc")
        self.catmenu.add_radiobutton(label = "cond-mat", variable = self.def_cat, value = "cond-mat")
        self.editmenu.add_cascade(label = "Default category", menu = self.catmenu)
        self.editmenu.add_separator()
        self.editmenu.add_command(label = "Count papers", command = self.count_papers)
        self.editmenu.add_command(label = "Select all papers", command = self.on_select_all)
        self.editmenu.add_separator()
        self.sortby = Menu(self.editmenu, tearoff = 0, font = self.listfont)
        self.sortby.add_command(label = "Date         Ctrl+D", command = self.on_sort_date)
        self.sortby.add_command(label = "Title          Ctrl+T", command = self.on_sort_title)
        self.editmenu.add_cascade(label = "Sort by...", menu = self.sortby)
        self.editmenu.add_command(label = "Find             Ctrl+F", command = self.on_menu_search)
        self.menu.add_cascade(label = "Edit", menu = self.editmenu)
        master.config(menu = self.menu)

        #Binding hotkeys
        master.bind("<Control-s>",lambda x: self.on_save_this_file())
        master.bind("<Control-S>",lambda x: self.on_save_file())
        master.bind("<Control-n>",lambda x: self.on_new_file())
        master.bind("<Control-o>",lambda x: self.on_open_file())
        master.bind("<Control-O>",lambda x: self.on_open_file_merge())
        master.bind("<Control-q>",lambda x: self.on_close())
        master.bind("<Control-f>",lambda x: self.on_menu_search())
        master.bind("<Control-d>",lambda x: self.on_sort_date())
        master.bind("<Control-t>",lambda x: self.on_sort_title())
        master.bind("<Control-a>",lambda x: self.on_select_all())
        master.bind("<Control-e>",lambda x: self.export_selected())
        #This is for disabling the buttons if one presses Esc
        master.bind("<Escape>", self.on_esc_press)
            
        master.bind("<Configure>", self.adjust_wraplength)

        #Grid everything
        masterl.columnconfigure(0, weight = 1)
        masterl.columnconfigure(1, weight = 1)
        masterl.columnconfigure(2, weight = 2)
        masterl.columnconfigure(3, weight = 0)
        masterr.columnconfigure(0, weight = 1)
        masterl.rowconfigure(1, weight = 1)
        masterl.rowconfigure(2, weight = 0)
        masterr.rowconfigure(4, weight = 1)
        self.paper_list.grid(row = 1, column = 0, columnspan = 3, sticky = "news")
        #self.dropdown_filter.grid(row = 0, column = 2, columnspan = 2, sticky = "news")
        self.add_paper.grid(row = 0, column = 0, sticky = "news")
        self.select_all.grid(row = 0, column = 1, sticky = "news")
        #
        self.paper_title.grid(row = 0, column = 0, columnspan = 4, sticky = "nwe")
        self.paper_authors.grid(row = 1, column = 0, columnspan = 4, sticky = "nwe")
        self.inspire_id.grid(row = 2, column = 0, sticky = "sw")
        self.arxiv_abs.grid(row = 2, column = 1, sticky = "se")
        self.arxiv_pdf.grid(row = 2, column = 2, sticky = "swe")
        self.get_bibtex.grid(row = 2, column = 3, sticky = "swe")
        self.text_box.grid(row = 3, column = 0, sticky = "news")
        self.bibentry.grid(row = 4, column = 0, columnspan = 4, sticky = "news")
        self.status_bar.grid(row = 5, column = 0, columnspan = 4, sticky = "news")
        #self.dropdown_set.grid(row = 3, column = 1, columnspan = 2, sticky = "news")
        self.update_paper.grid(row = 3, column = 3, sticky = "news")
        
        #For the tabbing order
        self.text_box.lift()
        self.bibentry.lift()

        #For redirecting stdout to the label status_bar
        class StandardOut():
            def __init__(self, obj, master, label):
                self.stream = obj
                self.master = master
                self.label = label
                self.grand_total = ""
                self.tooltip = CreateToolTip(master, label, text = "The history of the messages caps at 18 lines or 800 characters.")
            def write(self, text):
                #This also writes on the terminal
                #sys.__stdout__.write(text)
                if text != "\n" and len(text) > 0:
                    if text[0] == "\r":
                        text2 = text[1:]
                    else:
                        text2 = text
                        self.grand_total += text2
                    self.stream.set(text2)
                    self.master.update()
                else:
                    self.grand_total += "\n"
                while self.grand_total.count("\n") > 18:
                    pos = self.grand_total.find("\n") + 1
                    self.grand_total = self.grand_total[pos:]
                if len(self.grand_total) > 800:
                    self.grand_total = self.grand_total[-800:]
                self.tooltip.hidetip(master)
                self.tooltip = CreateToolTip(self.master, self.label, text = self.grand_total[:-1])
            def flush(self):
                pass

        sys.stdout = StandardOut(self.status, self.master, self.status_bar)

        #If the default file or given exitst, load it
        try:
            with open(default_filename, "r", encoding = "utf-8") as file:
                contents = file.read()
                self.biblio.parse(contents)
                #Drop down menus
                self.create_menus()
                self.load_data()
                #This makes the scrollbar start at the bottom at the initial loading
                self.paper_list.scrollbar.set(1.0,1.0)
                for c in self.paper_list.column_dict:
                    self.paper_list.column_dict[c].list_box.yview_moveto(1.0)
        except FileNotFoundError:
            if len(sys.argv) > 1:
                print("The given file is not available.")
            else:
                print("The default file is not available.")
            self.create_menus()
            self.on_new_file()

    def create_menus(self):
        """Creates the dropdown menus for filtering and selecting the paper category and also the one for exporting"""
        #For mapping the entries in the dict to the way they look in the menu
        if hasattr(self,"category_dict"):
            self.category_dict.update(self.biblio.cat_dict)
        else:
            self.category_dict = self.biblio.cat_dict
        self.category_dict_inv = {v:k for k,v in self.category_dict.items()}
        
        #Drop down menu for editing the paper category
        self.categories = list(self.category_dict.values()) + ["Other"]
        self.dropdown_set_val = StringVar()
        self.dropdown_set_val.set(self.categories[0])
        self.current_category = ""
        self.dropdown_set = OptionMenu(self.frame_right, self.dropdown_set_val, *self.categories)
        self.dropdown_set.config(font = self.listfont, width = 11)
        self.dropdown_set_val.trace_id = self.dropdown_set_val.trace("w", self.on_change_flags)   

        #Drop down menu for filtering the paper category
        self.dropdown_filter_val = StringVar()
        self.dropdown_filter_val.set(self.categories[0])
        self.dropdown_filter = OptionMenu(self.frame_left, self.dropdown_filter_val, command = self.on_filter, *self.categories[:-1])
        self.dropdown_filter.config(font = self.listfont)

        self.export.menus_already_there = []
        #Drop down menu for the export
        for cat in self.categories[1:-1]:
            self.export.add_command(label = cat, command = self.export_group(cat))
            self.export.menus_already_there.append(cat)

        #I have to grid them here
        self.dropdown_filter.grid(row = 0, column = 2, columnspan = 2, sticky = "news")
        self.dropdown_set.grid(row = 3, column = 1, columnspan = 2, sticky = "news")

    def export_group(self, cat):
        """Exports to a file only the papers that belong to a given group"""
        flag = self.category_dict_inv[cat]
        def f():
            filename = filedialog.asksaveasfilename(initialdir = self.current_folder(), title = "Select file", filetypes = (("BibTeX files", "*.bib"),("All files", "*.*")))
            try:
                with open(filename, "w+", encoding = "utf-8") as file:
                    for key, entry in self.biblio.entries.items():
                        if flag in entry.flags:
                            file.write(entry.write())
                        
            except (PermissionError,  TypeError, FileNotFoundError) as e:
                print("Error occurred when saving file.")
           
        return f

    def export_selected(self):
        """Exports to a file only the papers given in a selection"""
        sel = self.paper_list.curselection()
        entries = [self.biblio.entries[self.paper_list.get(a)[0]] for a in sel]
        filename = filedialog.asksaveasfilename(initialdir = self.current_folder(), title = "Select file", filetypes = (("BibTeX files", "*.bib"),("All files", "*.*")))
        if len(entries) == 0:
            print("There were no selected papers.")
            return False
        try:
            with open(filename, "w+", encoding = "utf-8") as file:
                for entry in entries:
                    file.write(entry.write())
                        
        except (PermissionError,  TypeError, FileNotFoundError) as e:
            print("Error occurred when saving file.")

    def right_click_popup(self, event):
            try:
                self.popup_menu.post(event.x_root, event.y_root)
            finally:
                self.popup_menu.grab_release()

    def toggle_arxiv_add(self, event = None):
        """Toggles whether the Arxiv number prompt pops up after pressing Add or not"""
        self.ask_arxiv_on_add = not self.ask_arxiv_on_add
        self.add_paper.configure(text = "Add" if self.ask_arxiv_on_add else "Add (no prompt)")

    def exit_popup(self, event):
        """Kills menu in the bibentry widget"""
        self.popup_menu.unpost()

    def enable_menu(self):
        """Shows menu in the bibentry widget"""
        if self.bibentry.tag_ranges(SEL):
            self.popup_menu.entryconfig(0, state = NORMAL)
            self.popup_menu.entryconfig(1, state = NORMAL)
            self.popup_menu.entryconfig(4, state = NORMAL)
            self.popup_menu.entryconfig(5, state = NORMAL)
        else:
            self.popup_menu.entryconfig(0, state = DISABLED)
            self.popup_menu.entryconfig(1, state = DISABLED)
            self.popup_menu.entryconfig(4, state = DISABLED)
            self.popup_menu.entryconfig(5, state = DISABLED)

    def on_cut(self):
        """Cut button on the Menu on the bibentry widged"""
        ranges = self.bibentry.tag_ranges(SEL)
        text = self.bibentry.get(*ranges)
        self.master.clipboard_clear()
        self.master.clipboard_append(text)
        text = text.replace("\n","")
        if len(text) > 41:
            text = text[0:19]+"..."+text[-19:]
        print(text + " copied to clipboard")
        self.bibentry.delete(*ranges)

    def on_copy(self):
        """Copy button on the Menu on the bibentry widged"""
        ranges = self.bibentry.tag_ranges(SEL)
        text = self.bibentry.get(*ranges)
        self.master.clipboard_clear()
        self.master.clipboard_append(text)
        text = text.replace("\n","")
        if len(text) > 41:
            text = text[0:19]+"..."+text[-19:]
        print(text + " copied to clipboard")

    def on_paste(self):
        """Paste button on the Menu on the bibentry widged"""
        try:
            text = self.master.clipboard_get()
        except:
            text = ""
        self.bibentry.insert(INSERT, text)

    def on_indent(self):
        """Indent button on the Menu on the bibentry widged"""
        indentation = 6
        ranges = self.bibentry.tag_ranges(SEL)
        ranges = self.bibentry.index(ranges[0]) + "linestart", self.bibentry.index(ranges[1])
        text = self.bibentry.get(*ranges)
        text = indentation*" " + text.replace("\n", "\n" + indentation*" ")
        self.bibentry.delete(*ranges)
        self.bibentry.insert(ranges[0], text)

    def on_deindent(self):
        """De-indent button on the Menu on the bibentry widged"""
        indentation = 6
        ranges = self.bibentry.tag_ranges(SEL)
        ranges = self.bibentry.index(ranges[0]) + "linestart", self.bibentry.index(ranges[1])
        text = self.bibentry.get(*ranges)
        lines = text.split("\n")
        newlines = []
        for l in lines:
            ll = re.sub('^ {0,' + str(indentation) + "}", "", l)
            newlines.append(ll)
        text = "\n".join(newlines)
        self.bibentry.delete(*ranges)
        self.bibentry.insert(ranges[0], text)

    def adjust_wraplength(self, event = None):
        """Readjust wraplength on resize"""
        w = event.width if event is not None else self.master.winfo_height()
        self.paper_title.adjust_wraplength(w)
        self.paper_authors.adjust_wraplength(w)

    def copy_to_clipboard(self, event = None):
        """Copies the inspire_id text to the system clipboard"""
        self.master.clipboard_clear()
        self.master.clipboard_append(self.inspire_text.get())
        print(self.inspire_text.get() + " copied to clipboard")

    def current_folder(self):
        """Simply returns the folder containing self.current_file"""
        if self.current_file == None:
            return "~"
        else:
            folder = os.path.dirname(self.current_file)
            return folder

    def disable_buttons(self):
        """The two buttons start as disabled at every load.
           Enable them once and make this function trivial when called again"""
        self.get_bibtex.config(state = DISABLED)
        self.update_paper.config(state = DISABLED)
        self.dropdown_set.config(state = DISABLED)
        self.editmenu.entryconfig(2, state = DISABLED)
        self.editmenu.entryconfig(3, state = DISABLED)
        def g():
            self.dropdown_set.config(state = NORMAL)
            self.update_paper.config(state = NORMAL)
            self.editmenu.entryconfig(2, state = NORMAL)
            self.get_bibtex.config(state = NORMAL)
            self.editmenu.entryconfig(3, state = NORMAL)
            def f():
                pass
            self.enable_buttons = f
        self.enable_buttons = g
  
    def on_esc_press(self, event):
        if event.widget in [w.list_box for w in self.paper_list.column_dict.values()]:
            self.disable_buttons()

    def count_papers(self):
        print("There are currently {} papers.".format(len(self.biblio.entries.keys())))

    def load_data(self):
        """Loads the data on the listbox"""
        self.paper_list.delete(0, END)
        self.disable_buttons()

        for key, entry in self.biblio.entries.items():
            if entry.visible:
                self.paper_list.insert(END, entry.inspire_id, entry.initials, entry.description)

    def list_has_changed(self, selection):
        """Event: selection has changed"""
        if len(selection) == 1:
            self.enable_buttons()
            
            sel = selection[0]
            entry = self.biblio.entries[self.paper_list.get(sel)[0]]

            self.paper_title.latex_set(entry.title)
            self.arxiv_link.set(entry.arxiv_no)
            self.inspire_text.set(entry.inspire_id)
            self.comment.set(entry.description)

            #Here I temporarily suppress the callback to put the dropdown menu on Other
            self.dropdown_set_val.trace_vdelete("w", self.dropdown_set_val.trace_id)
            self.dropdown_set_val.set(self.category_dict.get(entry.flags,"Other"))
            self.dropdown_set_val.trace_id = self.dropdown_set_val.trace("w", self.on_change_flags)
            #Then I set the flags
            self.current_category = entry.flags

            #Writes the authors and binds links to them
            def url(auth):
                return "http://inspirehep.net/search?&p=a+{1},+{0}&sf=earliestdate&so=d".format(*auth)
            text = "{} {}".format(*(entry.authors[0]))
            self.paper_authors.text_set("")
            self.paper_authors.link_add(text, url(entry.authors[0]))
            for nm, lnm in entry.authors[1:]:
                text = "{} {}".format(nm, lnm)
                self.paper_authors.text_add(", ")
                self.paper_authors.link_add(text, url((nm, lnm)))
                
            self.remove_info()
            self.adjust_wraplength()
            self.bibentry.insert(1.0, entry.bibentry)
            
        elif len(selection) > 1:
            self.enable_buttons()
            entries = [self.biblio.entries[self.paper_list.get(sel)[0]] for sel in selection]

            self.paper_title.latex_set("Multiple selection")
            self.arxiv_link.set("Multiple links")
            self.inspire_text.set("<id>")
            self.comment.set(f"{len(selection)} papers selected.")

            #Here I temporarily suppress the callback to put the dropdown menu on Other
            self.dropdown_set_val.trace_vdelete("w", self.dropdown_set_val.trace_id)
            self.dropdown_set_val.set("All")
            self.current_category = None
            self.dropdown_set_val.trace_id = self.dropdown_set_val.trace("w", self.on_change_flags)

            #Writes the authors and binds links to them, only if they are less than 10
            all_authors = []
            maxauthors = 10 
            for e in entries:
                all_authors += [a for a in e.authors if a not in all_authors]
            all_authors.sort(key = lambda x:x[1])
            if len(all_authors) > maxauthors:
                    all_authors = all_authors[:maxauthors] + [("+", str(len(all_authors) - maxauthors))]
            def url(auth):
                return "http://inspirehep.net/search?&p=a+{1},+{0}&sf=earliestdate&so=d".format(*auth)
            text = "{} {}".format(*(all_authors[0]))
            self.paper_authors.text_set("")
            self.paper_authors.link_add(text, url(all_authors[0]))
            for nm, lnm in all_authors[1:]:
                text = "{} {}".format(nm, lnm)
                self.paper_authors.text_add(", ")
                if nm == "+":
                    self.paper_authors.text_add(f"{lnm} more...")
                else:
                    self.paper_authors.link_add(text, url((nm, lnm)))
                
            self.remove_info()
            self.adjust_wraplength()
            self.bibentry.config(fg = "gray35")
            #Ok, this is kind of weird, but I have a check that makes the color back to black only if there is something bound to <1>
            self.bibentry.binding = self.bibentry.bind("<1>", lambda x: None)
            if overwrite_flags:
                line1 = "overwrites instead of adding"
            else:
                line1 = "adds instead of overwriting"
            self.bibentry.insert(1.0,f"Changing the groups from the \"Other\" menu {line1}.\n\n"
                                 "The Get Bibtex button automatically updates all selected papers.\n\n"
                                 "The PDF and abstract page buttons open up to a maximum of 10 tabs.")
            
    def on_arxiv_abs(self):
        """Event: load arxiv abstract page"""
        def f():
            url = "https://arxiv.org/abs/{}"
            if self.arxiv_link.get() != "n/a":
                if self.arxiv_link.get() != "Multiple links":
                    webbrowser.open_new_tab(url.format(self.arxiv_link.get()))
                else:
                    selection = self.paper_list.curselection()
                    links = [self.biblio.entries[self.paper_list.get(sel)[0]].arxiv_no for sel in selection]
                    if len(links) > 10:
                        links = links[:10]
                    for l in links:
                        webbrowser.open_new_tab(url.format(l))
            else:
                print("ArXiv number not available.")
        return f

    def on_arxiv_pdf(self):
        """Event: load arxiv PDF page"""
        def f():
            url = "https://arxiv.org/pdf/{}.pdf"
            if self.arxiv_link.get() != "n/a":
                if self.arxiv_link.get() != "Multiple links":
                    webbrowser.open_new_tab(url.format(self.arxiv_link.get()))
                else:
                    selection = self.paper_list.curselection()
                    links = [self.biblio.entries[self.paper_list.get(sel)[0]].arxiv_no for sel in selection]
                    if len(links) > 10:
                        links = links[:10]
                    for l in links:
                        webbrowser.open_new_tab(url.format(l))
            else:
                print("ArXiv number not available.")
        return f

    def on_get_bibtex(self):
        """Event: load on textbox the Bibtex entry from Inspire"""
        link = self.arxiv_link.get()
        if self.arxiv_link.get() in ["n/a", ""]:
            #link = simpledialog.askstring(title="Preprint number",
            #                              prompt="Insert here the preprint number:")
            d = Arxiv_prompt(self, lambda : Query.list_papers(self.def_cat.get()))
            self.master.wait_window(d.choose)
            link = d.response 
            if link is None or link is "":
                print("I did not do anything.")
                return None
        if self.arxiv_link.get() == "Multiple links":
            self.update_all()
        else:
            try:
                text = Query.get(link)
            except Query.PaperNotFound:
                return None
            else:
                self.remove_info()
                self.bibentry.insert(1.0, text)

    def on_change_flags(self, *args):
        """Event called when a new value from the selection dropdown menu is changed"""
        if self.dropdown_set_val.get() == "Other":
            #Insert here the call to a new window for selecting the categories
            s = Category_Selection(self, self.current_category)
            self.master.wait_window(s.sel)
            response = s.response

            self.biblio.cat_dict.update(response)
            self.current_category = ""
            for a in list(response.keys()):
                self.current_category += a

            #Here I do part of the things done in create_menu(). I do not recall it to avoid recursion
            self.category_dict = self.biblio.cat_dict
            self.category_dict_inv = {v:k for k,v in self.category_dict.items()}
            self.categories = list(self.category_dict.values()) + ["Other"]

            self.dropdown_set_val.trace_vdelete("w", self.dropdown_set_val.trace_id)
            self.dropdown_set_val.set("Other" if len(self.current_category) > 1 else self.category_dict[self.current_category])
            self.dropdown_set = OptionMenu(self.frame_right, self.dropdown_set_val, *self.categories)
            self.dropdown_filter = OptionMenu(self.frame_left, self.dropdown_filter_val, command = self.on_filter, *self.categories[:-1])
            self.dropdown_set_val.trace_id = self.dropdown_set_val.trace("w", self.on_change_flags)

            self.dropdown_set.config(font = self.listfont, width = 11)
            self.dropdown_filter.config(font = self.listfont)

            #Adding the groups to the export menu
            for cat in self.categories[1:-1]:
                if not cat in self.export.menus_already_there:
                    self.export.add_command(label = cat, command = self.export_group(cat))
                    self.export.menus_already_there.append(cat)

            #I have to grid them here
            self.dropdown_filter.grid(row = 0, column = 2, columnspan = 2, sticky = "news")
            self.dropdown_set.grid(row = 3, column = 1, columnspan = 2, sticky = "news")
            
        else:
            self.current_category = self.category_dict_inv[self.dropdown_set_val.get()]

    def on_update(self):
        """Event: the button "Update" has been pressed"""        
        bib = self.bibentry.get(1.0, END)
        com = self.comment.get().replace("|"," ").replace("}"," ").replace("}"," ")
        flag = self.current_category
        sel = self.paper_list.curselection()
        ent = self.inspire_text.get()
        remember_bib = self.biblio.entries[ent].bibentry if not ent == "<id>" else ""

        if len(sel) <= 1:
            #Modify or add only one paper
            if not ent == "":
                if not ent == "<id>":
                    del self.biblio.entries[ent]
                    self.paper_list.delete(sel)
                else:
                    sel = END
                try:
                    ent = self.biblio.parse_raw_entry(bib, True)
                except:
                    if not ent == "<id>":
                        print("An error occurred in parsing. I reverted the entry to its old state.")
                        ent = self.biblio.parse_raw_entry(remember_bib)
                    else:
                        print("An error occurred in parsing. I did not do anything.")
                        return None
                else:
                    print("Entry updated.")

                if ent in self.biblio.comment_entries.keys():
                    self.biblio.comment_entries[ent].update({"description": com, "category": flag})
                else:
                    self.biblio.comment_entries.update({ent : {"description": com, "category": flag}})

                entry = self.biblio.entries[ent]
                self.biblio.link_comment_entry(entry)
                self.paper_list.insert(sel, entry.inspire_id, entry.initials, entry.description)
                self.paper_list.selection_set(sel)
                self.list_has_changed((sel,))

        elif flag is not None:
            #Modify the flags of a group of papers
            entlist = [self.paper_list.get(s)[0] for s in sel]
            def merge(str1, str2):
                if overwrite_flags:
                    ret = str2
                else:
                    ret = str1
                    for c in str2:
                        if c not in ret:
                            ret += c
                return ret
            for en in entlist:
                if en in self.biblio.comment_entries.keys():
                    iniflag = self.biblio.comment_entries[en]["category"]
                    #The flags are added to the existing ones or overwritten.
                    #It depends on the value of the global variable overwrite_flags
                    self.biblio.comment_entries[en].update({"category": merge(iniflag, flag)})
                else:
                    self.biblio.comment_entries.update({en : {"description": "Not found", "category": flag}})
                entry = self.biblio.entries[en]
                self.biblio.link_comment_entry(entry)
            if flag == "":
                if overwrite_flags:
                    print(f"The group(s) have been cleared from {len(sel)} entries.")
                else:
                    print("I did not do anything.")
            else:
                flaglong = ",".join([self.category_dict[a] for a in flag])
                grp,has = ("", "s") if len(flag) == 1 else ("s", "ve")
                added = "assigned" if overwrite_flags else "added"
                print(f"The group{grp} {flaglong} ha{has} been {added} to {len(sel)} entries.")
        else:
            print("I did not do anything.")
            return 0

        self.is_modified = True
        if self.current_file == None:
            master.title("*Bibliography - Untitled")
        else:
            master.title("*Bibliography - " + self.current_file.split("/")[-1])

    def remove_info(self, event = None):
        """If the info message in grey is showing in the text box removes that and reverts the configuration, otherwise just erases the textbox."""
        if self.bibentry.binding is not None:
            self.bibentry.unbind("<1>", self.bibentry.binding)
            self.bibentry.config(fg = "black")
        self.bibentry.delete(1.0, END)
        self.bibentry.binding = None

    def on_add(self):
        """Add an item"""
        self.paper_list.selection_clear(0,END)

        self.bibentry.delete(1.0, END)
        self.bibentry.insert(1.0,"%%Click on \"Get Bibtex\" to insert the ArXiv number and load the Bibtex entry or type the Bibtex entry here.%%"+
                                 "\n\n@article{Author:2020abc,\n"
                                 "         ...\n"
                                 "}")
        self.bibentry.config(fg = "gray35")
        self.bibentry.binding = self.bibentry.bind("<1>", self.remove_info)

        self.comment.set("Insert description here.")
        self.inspire_text.set("<id>")
        self.paper_title.text_set("Title")
        self.paper_authors.text_set("Authors")
        self.arxiv_link.set("n/a")
        self.dropdown_set_val.set(self.category_dict[""])

        self.enable_buttons()
        if self.ask_arxiv_on_add:
            self.on_get_bibtex()

    def on_select_all(self):
        """Selects all papers"""
        self.paper_list.selection_set(0,END)

    def on_remove(self):
        """Remove an item"""
        sel = self.paper_list.curselection()
        if len(sel) > 0:
            entries = [(s, self.paper_list.get(s)[0]) for s in sel]
            for s,ent in sorted(entries,key=lambda x:x[0], reverse=True):
                del self.biblio.entries[ent]
                self.paper_list.delete(s)
    
            self.paper_list.selection_clear(0,END)
            self.bibentry.delete(1.0, END)
            self.comment.set("")
            self.inspire_text.set("")
            self.paper_title.text_set("")
            self.paper_authors.text_set("")
            self.arxiv_link.set("n/a")
            self.dropdown_set_val.set("All")
            
            entries = [a[1] for a in entries]
            if len(entries) > 5:
                entries = entries[:4] + ["..."] + entries[-1:]
            removed = ",".join(entries)
            ess = "" if len(entries) == 1 else "s"
            print(f"Removed paper{ess} with Inspire ID {removed}.")

            self.is_modified = True
            if self.current_file == None:
                master.title("*Bibliography - Untitled")
            else:
                master.title("*Bibliography - " + self.current_file.split("/")[-1])
            self.disable_buttons()

    def on_search(self, event = None):
        """Search for a pattern"""
        self.dropdown_filter_val.set("Search results")
        query = self.biblio.parse_search(self.search_string.get())
        self.biblio.filter(query)
        self.load_data()

    def on_exit_search(self, event = None):
        """Closes the search"""
        self.dropdown_filter_val.set("All")
        self.on_filter()
        
    def on_menu_search(self, event = None):
        """Shows the search widgets and focuses on the search textbox"""
        self.search_box.focus_set()
        self.search_box.grid(row = 2, column = 0, columnspan = 2, sticky = "news")
        self.search_button.grid(row = 2, column = 2, columnspan = 2, sticky = "news")

    def on_filter(self, event = None):
        """The filter dropdown menu has changed"""
        self.tooltip.hidetip(self.master)
        self.search_box.grid_forget()
        self.search_button.grid_forget()

        flag = self.category_dict_inv[self.dropdown_filter_val.get()]
        for key, e in self.biblio.entries.items():
            if flag in e.flags:
                e.visible = True
            else:
                e.visible = False

        self.load_data()

    def on_sort_date(self):
        """Sorts by date"""
        self.biblio.sort_by(lambda x: x.date)
        self.load_data()
        self.is_modified = True
        if self.current_file == None:
            master.title("*Bibliography - Untitled")
        else:
            master.title("*Bibliography - " + self.current_file.split("/")[-1])

    def on_sort_title(self):
        """Sorts by title"""
        self.biblio.sort_by(lambda x: x.title)
        self.load_data()
        self.is_modified = True
        if self.current_file == None:
            master.title("*Bibliography - Untitled")
        else:
            master.title("*Bibliography - " + self.current_file.split("/")[-1])

    def update_all(self):
        """Updates the bibtex entries of all papers"""
        count = 0
        animation = 0
        sys.stdout.write("Fetching data from Inspire...|")
        sel = self.paper_list.curselection()
        if len(sel) > 0:
            entries = [self.biblio.entries[self.paper_list.get(a)[0]] for a in sel]
        else:
            entries = self.biblio.entries.values()
        for el in entries:
            if el.arxiv_no not in ["n/a", ""]:
                animation += 1
                try:
                    text = Query.get(el.arxiv_no, 0)
                    if el.bibentry != text:
                        count += 1
                        el.bibentry = text
                except Query.PaperNotFound:
                    sys.stdout.write("\rPaper with eprint {} not found.\n".format(el.arxiv_no))
                    sys.stdout.flush()
                else:
                    #This is just an animation to show that the program is not frozen
                    sys.stdout.write("\rFetching data from Inspire...{}".format(["|","/","-","\\"][animation % 4]))
                    sys.stdout.flush()
        sys.stdout.write("\rFetching data from Inspire... \n")
        if count == 1:
            print("Updated 1 entry.")
        else:
            print("Updated {} entries.".format(count))
        if count > 0:
            self.is_modified = True
            if self.current_file == None:
                master.title("*Bibliography - Untitled")
            else:
                master.title("*Bibliography - " + self.current_file.split("/")[-1])
            if self.paper_list.curselection() != ():
               self.list_has_changed(self.paper_list.curselection())

    def on_new_file(self):
        """Creates a new file"""
        self.biblio.entries = {}
        self.biblio.comment_entries = {}
        self.load_data()
        self.current_file = None

        self.is_modified = False
        master.title("Bibliography - Untitled")
        

    def on_open_file(self):
        """Opens a .bib file with comments compatible with this application. Discards current state of the biblio"""
        filename = filedialog.askopenfilename(initialdir = self.current_folder(), title = "Select file", filetypes = (("BibTeX files", "*.bib"),("All files", "*.*")))
        try:
            with open(filename, "r", encoding = "utf-8") as file:
                self.biblio.entries = {}
                self.biblio.comment_entries = {}
                self.biblio.cat_dict = {}
                self.category_dict = {}
                contents = file.read()
                self.biblio.parse(contents)
                self.create_menus()
                self.load_data()

                self.current_file = filename
                self.is_modified = False
                master.title("Bibliography - " + filename.split("/")[-1])
        except (FileNotFoundError, TypeError) as e:
            print("Error occurred when loading file.")

    def on_open_file_merge(self):
        """Opens a .bib file with comments compatible with this application. Merges the content of the current biblio"""
        filename = filedialog.askopenfilename(initialdir = self.current_folder(), title = "Select file", filetypes = (("BibTeX files", "*.bib"),("All files", "*.*")))
        try:
            with open(filename, "r", encoding = "utf-8") as file:
                contents = file.read()
                self.biblio.parse(contents)
                self.create_menus()
                self.load_data()

                self.current_file = filename
                self.is_modified = True
                master.title("*Bibliography - " + filename.split("/")[-1])
        except (FileNotFoundError, TypeError) as e:
            print("Error occurred when loading file.")
                

    def on_save_file(self):
        """Saves a .bib file with comments compatible with this application."""
        filename = filedialog.asksaveasfilename(initialdir = self.current_folder(), title = "Select file", filetypes = (("BibTeX files", "*.bib"),("All files", "*.*")))
        try:
            with open(filename, "w+", encoding = "utf-8") as file:
                file.write(self.biblio.comment_string())
                for key, entry in self.biblio.entries.items():
                    file.write(entry.write())
                    
                self.current_file = filename
                self.is_modified = False
                master.title("Bibliography - " + filename.split("/")[-1])
        except (PermissionError,  TypeError, FileNotFoundError) as e:
            print("Error occurred when saving file.")

    def on_save_this_file(self):
        """Saves a .bib file with comments compatible with this application. Saves on the current file"""
        if self.current_file == None:
            self.on_save_file()
        else:
            try:
                with open(self.current_file, "w+", encoding = "utf-8") as file:
                    file.write(self.biblio.comment_string())
                    for key, entry in self.biblio.entries.items():
                        file.write(entry.write())

                    self.is_modified = False
                    master.title("Bibliography - " + self.current_file.split("/")[-1])       
            except PermissionError:
                print("Error occurred when saving file.")

    def on_close(self):
        """Closes the main window"""
        if self.is_modified:
            if messagebox.askokcancel("Quit?","The last modifications will be discarded."):
                self.master.destroy()
                self.master.quit()
        else:
            self.master.destroy()
            self.master.quit()          
        

master = Tk()
biblio = Biblio()
root   = Root(master, biblio)

master.mainloop()
