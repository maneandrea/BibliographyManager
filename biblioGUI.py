from tkinter import *
from tkinter import messagebox, filedialog, simpledialog, font
import webbrowser, urllib.request
import os, sys, time
import subprocess
from datetime import datetime
import copy

# My packages
import biblioDB
from otherWidgets import *  # Some functionalities are compatible with TkTreectrl
from biblioDB import *
from inspireQuery import *

icon = os.path.join(os.path.dirname(__file__),"Icons","icon.png")

"""
Add the Undo-Redo functionalities to the bibentry textbox
Fix the clunky LaTeX rendering in the titles
"""


class Root:
    """This is the main window"""

    def __init__(self, master, bibliography, *args, **kwargs):

        self.sysargv = args
        for key, val in kwargs.items():
            self.__setattr__(key, val)

        # The Biblio object with which we interact
        self.biblio = bibliography

        # For Save / Save As
        self.current_file = self.default_filename
        self.is_modified = False

        # Asks the Arxiv number right after pressing Add
        self.ask_arxiv_on_add = True

        # Stops the process that updates the bibtex of all the papers at once
        self.interrupt_process = False

        # Window config
        self.master = master
        master.protocol("WM_DELETE_WINDOW", self.on_close)
        master.call('wm', 'iconphoto', master._w, PhotoImage(file=icon))
        master.title("Bibliography - " + self.current_file.split("/")[-1])
        self.paned = PanedWindow(master)
        self.paned.config(sashrelief=RAISED, sashwidth=8)
        ini_halfwidth = 600
        ini_height = 600
        #master.geometry(
        #    f"{2 * ini_halfwidth}x{ini_height}+{master.winfo_screenwidth() // 6}+{master.winfo_screenheight() // 6}")

        # Left and right panels
        self.frame_left = Frame(self.paned)
        self.frame_right = Frame(self.paned)
        self.frame_left.config(width=ini_halfwidth, height=ini_height)
        self.frame_right.config(width=ini_halfwidth, height=ini_height)
        masterl = self.frame_left
        masterr = self.frame_right
        self.paned.add(masterl)
        self.paned.add(masterr)
        self.paned.pack(fill=BOTH, expand=1)

        # Define fonts
        self.listfont = font.Font(family="DejaVu Sans", size=12)
        self.columnfont = font.Font(family="DejaVu Sans", size=12, slant="italic")
        LMSS = "Calibri" if os.name == "nt" else "Latin Modern Sans"
        self.titlefont = font.Font(family=LMSS, size=20, weight="bold")
        self.authorsfont = font.Font(family=LMSS, size=16)
        DEJAVUSANSMONO = "Lucida Sans Typewriter" if os.name == "nt" else "DejaVu Sans Mono"
        self.bibentryfont = font.Font(family=DEJAVUSANSMONO, size=13)

        # MultiListbox config
        self.paper_list = MultiListbox(masterl)
        self.paper_list.config(columns=("Inspire ID", "Authors", "Description"), font=self.listfont,
                               selectcmd=self.list_has_changed, columnfont=self.columnfont,
                               bg='white' if int(self.frame_right.cget('bg').replace('#','0x'),16) > 8388607 else '#222222')
        # This fixes the initial widths of the columns
        self.paper_list.set_widths(100, 80)
        # This binds Sort by Date to the first column and Sort by Title to the Last
        self.paper_list.bind_command("Inspire ID", self.on_sort_date)
        self.paper_list.bind_command("Description", self.on_sort_title)
        # This adds the tooltips
        self.tooltip_datesort = CreateToolTip(master, self.paper_list.column_dict["Inspire ID"].top,
                                              text="Sort by date (Not Inspire ID)")
        self.tooltip_titlesort = CreateToolTip(master, self.paper_list.column_dict["Description"].top,
                                               text="Sort by title (Not description)")

        # Title config: LatexText is a widget based on text that is able to render LaTeX
        self.paper_title = LatexText(masterr)
        self.paper_title.config(font=self.titlefont, state=DISABLED,
                                height=1, bg=masterr.cget('bg'), relief=FLAT, wrap=WORD)
        self.paper_title.bindtags((str(self.paper_title), str(masterr), "all"))

        # Authors config: HyperrefText is a widget based on Text that is able to contain hypertext
        self.paper_authors = HyperrefText(masterr)
        self.paper_authors.config(font=self.authorsfont, state=DISABLED,
                                  height=1, bg=masterr.cget('bg'), relief=FLAT, wrap=WORD, cursor="arrow")
        self.paper_authors.bindtags((str(self.paper_authors), str(masterr), "all"))

        # Text box
        self.bibentry = Text(masterr)
        self.bibentry.config(font=self.bibentryfont,
                             bg='white' if int(self.frame_right.cget('bg').replace('#','0x'),16) > 8388607 else '#222222')
        self.bibentry.bind("<<Paste>>", self.custom_paste)
        # This will represent the binding to <1> that removes the info message on the bibentry that appears after doing "Add"
        self.bibentry.binding = None

        # Right-click menu for the textbox
        self.popup_menu = Menu(self.master, tearoff=0, postcommand=self.enable_menu)
        self.popup_menu.add_command(label="Cut",
                                    command=self.on_cut, state=DISABLED)
        self.popup_menu.add_command(label="Copy",
                                    command=self.on_copy, state=DISABLED)
        self.popup_menu.add_command(label="Paste",
                                    command=self.custom_paste)
        self.popup_menu.add_separator()
        self.popup_menu.add_command(label="Indent",
                                    command=self.on_indent, state=DISABLED)
        self.popup_menu.add_command(label="De-indent",
                                    command=self.on_deindent, state=DISABLED)
        self.bibentry.bind("<Button-3>", self.right_click_popup)
        self.popup_menu.bind("<Leave>", self.exit_popup)

        # Label with inspire id
        self.inspire_text = StringVar()
        self.inspire_id = Entry(masterr)
        self.inspire_id.config(state="readonly", textvariable=self.inspire_text,
                               font=self.listfont, relief=FLAT, readonlybackground=masterr.cget('bg'))
        self.inspire_id.bind("<Double-Button-1>", self.copy_to_clipboard)

        # Buttons with links to the ArXiv
        self.arxiv_link = StringVar()
        self.arxiv_abs = Button(masterr)
        self.arxiv_pdf = Button(masterr)
        self.arxiv_abs.config(textvariable=self.arxiv_link, font=self.listfont, command=self.on_arxiv_abs())
        self.arxiv_pdf.config(text="PDF", font=self.listfont, command=self.on_arxiv_pdf())

        # Button that gets the bibtex text from Inspire
        self.get_bibtex = Button(masterr)
        self.get_bibtex.config(text="Get Bibtex", font=self.listfont, command=self.on_get_bibtex, state=DISABLED)

        # Text box to edit the paper comments
        self.comment = StringVar()
        self.text_box = Entry(masterr)
        self.text_box.config(font=self.listfont, textvariable=self.comment,
                             bg='white' if int(self.frame_right.cget('bg').replace('#','0x'),16) > 8388607 else '#222222')
        self.text_box.bind("<Return>", lambda x: self.on_update())
        self.text_box.bind("<<Paste>>", self.custom_paste)

        # Button for updating the new data
        self.update_paper = Button(masterr)
        self.update_paper.config(text="Update", font=self.listfont, command=self.on_update, state=DISABLED)

        # Buttons for deleting and adding
        self.add_paper = Button(masterl)
        self.select_all = Button(masterl)
        self.add_paper.config(text="Add", font=self.listfont, command=self.on_add)
        self.add_paper.bind("<3>", self.toggle_arxiv_add)
        self.select_all.config(text="Select All", font=self.listfont, command=self.on_select_all)

        # Textbox and button for searching
        self.search_button = Button(masterl)
        self.search_button.config(text="Search", font=self.listfont, command=self.on_search)
        self.search_string = StringVar()
        self.search_box = Entry(masterl)
        self.search_box.config(textvariable=self.search_string, font=self.listfont,
                               bg='white' if int(self.frame_right.cget('bg').replace('#','0x'),16) > 8388607 else '#222222')
        self.search_box.bind("<<Paste>>", self.custom_paste)
        self.tooltip = CreateToolTip(master, self.search_box,
                                     text="Prepend a to search by author, t by title, d by description, "
                                          "n by ArXiv number and nothing by all.\nGroup words with quotes. The search ignores cases.")
        self.search_box.search_history = []
        self.search_box.history_count = 0
        self.search_box.temp = ""

        # Local pdf
        self.local_pdf_label = Label(masterr)
        self.local_pdf_str = StringVar()
        self.local_pdf_label.config(textvariable=self.local_pdf_str, font=self.listfont, anchor=W, relief=SUNKEN,
                                    justify=LEFT, height=1)
        self.current_pdf_path = ""

        # Status bar
        self.status_bar = Label(masterr)
        self.status = StringVar()
        self.status_bar.config(textvariable=self.status, font=self.listfont, anchor=W, relief=SUNKEN,
                               justify=LEFT, height=1)
        self.status_bar.bind("<1>", self.on_status_bar_click)

        # Variables for the arxiv category
        self.def_cat = StringVar()
        self.def_cat.set(self.ini_def_cat)

        # Menu
        self.menu = Menu(master, font=self.listfont)
        self.filemenu = Menu(self.menu, tearoff=0, font=self.listfont)
        self.filemenu.add_command(label="New                         Ctrl+N", command=self.on_new_file)
        self.filemenu.add_command(label="Open...                    Ctrl+O", command=self.on_open_file)
        self.filemenu.add_command(label="Open and merge... Ctrl+Shift+O", command=self.on_open_file_merge)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Save...                     Ctrl+S", command=self.on_save_this_file)
        self.filemenu.add_command(label="Save As...                Ctrl+Shift+S", command=self.on_save_file)
        self.filemenu.add_command(label="Save (no comments)                ", command=self.on_save_nocomments)
        self.filemenu.add_separator()
        self.export = Menu(self.filemenu, tearoff=0, font=self.listfont)
        self.filemenu.add_cascade(label="Export...", menu=self.export)
        self.filemenu.add_command(label="See .bib file", command=self.see_bibfile)
        self.export.add_command(label="Selected                  Ctrl+E", command=self.export_selected("w"))
        self.export.add_command(label="Selected (append)  Ctrl+Shift+E", command=self.export_selected("a"))
        self.export.add_command(label="From .bbl", command=self.export_from_bbl)
        self.export.add_separator()
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit                          Ctrl+Q", command=self.on_close)
        self.menu.add_cascade(label="File", menu=self.filemenu)
        #
        self.editmenu = Menu(self.menu, tearoff=0, font=self.listfont)
        self.editmenu.add_command(label="Add", command=self.on_add)
        self.editmenu.add_command(label="Remove", command=self.on_remove)
        self.editmenu.add_command(label="Update", command=self.on_update)
        self.editmenu.add_command(label="Get Bibtex", command=self.on_get_bibtex)
        self.catmenu = Menu(self.editmenu, tearoff=0, font=self.listfont)
        self.catmenu.add_radiobutton(label="hep-th", variable=self.def_cat, value="hep-th")
        self.catmenu.add_radiobutton(label="hep-ph", variable=self.def_cat, value="hep-ph")
        self.catmenu.add_radiobutton(label="hep-lat", variable=self.def_cat, value="hep-lat")
        self.catmenu.add_radiobutton(label="math-ph", variable=self.def_cat, value="math-ph")
        self.catmenu.add_radiobutton(label="gr-qc", variable=self.def_cat, value="gr-qc")
        self.catmenu.add_radiobutton(label="cond-mat", variable=self.def_cat, value="cond-mat")
        self.editmenu.add_cascade(label="Default category", menu=self.catmenu)
        self.editmenu.add_separator()
        self.editmenu.add_command(label="Count papers", command=self.count_papers)
        self.editmenu.add_command(label="Select all papers", command=self.on_select_all)
        self.editmenu.add_separator()
        self.sortby = Menu(self.editmenu, tearoff=0, font=self.listfont)
        self.sortby.add_command(label="Date         Ctrl+D", command=self.on_sort_date)
        self.sortby.add_command(label="Title          Ctrl+T", command=self.on_sort_title)
        self.editmenu.add_cascade(label="Sort by...", menu=self.sortby)
        self.editmenu.add_command(label="Find             Ctrl+F", command=self.on_menu_search)
        self.menu.add_cascade(label="Edit", menu=self.editmenu)
        #
        self.pdfmenu = Menu(self.menu, tearoff=0, font=self.listfont)
        self.pdfmenu.add_command(label="Open PDF online", command=self.on_arxiv_pdf(True))
        self.pdfmenu.add_command(label="Open local PDF", command=self.on_arxiv_pdf(), state=DISABLED)
        self.pdfmenu.add_command(label="Open abstract page", command=self.on_arxiv_abs())
        self.pdfmenu.add_separator()
        self.pdfmenu.add_command(label="Link to local PDF", command=self.on_link_pdf)
        self.pdfmenu.add_command(label="Unlink from local PDF", command=self.on_unlink_pdf)
        self.pdfmenu.add_command(label="Save PDF locally and link", command=self.on_save_pdf)
        self.menu.add_cascade(label="PDF", menu=self.pdfmenu)
        #
        master.config(menu=self.menu)

        # Binding hotkeys
        master.bind("<Control-s>", lambda x: self.on_save_this_file())
        master.bind("<Control-S>", lambda x: self.on_save_file())
        master.bind("<Control-n>", lambda x: self.on_new_file())
        master.bind("<Control-o>", lambda x: self.on_open_file())
        master.bind("<Control-O>", lambda x: self.on_open_file_merge())
        master.bind("<Control-q>", lambda x: self.on_close())
        master.bind("<Control-f>", lambda x: self.on_menu_search())
        master.bind("<Control-d>", lambda x: self.on_sort_date())
        master.bind("<Control-t>", lambda x: self.on_sort_title())
        master.bind("<Control-a>", lambda x: self.on_select_all())
        master.bind("<Control-c>", lambda x: self.on_keyboard_interrupt())
        master.bind("<Control-e>", lambda x: self.export_selected("w")())
        master.bind("<Control-E>", lambda x: self.export_selected("a")())
        # This is for disabling the buttons if one presses Esc
        master.bind("<Escape>", self.on_esc_press)

        master.bind("<Configure>", self.adjust_wraplength)

        # Grid everything
        masterl.columnconfigure(0, weight=1)
        masterl.columnconfigure(1, weight=1)
        masterl.columnconfigure(2, weight=2)
        masterl.columnconfigure(3, weight=0)
        masterr.columnconfigure(0, weight=1)
        masterl.rowconfigure(1, weight=1)
        masterl.rowconfigure(2, weight=0)
        masterr.rowconfigure(4, weight=1)
        self.paper_list.grid(row=1, column=0, columnspan=3, sticky="news")
        # self.dropdown_filter.grid(row = 0, column = 2, columnspan = 2, sticky = "news")
        self.add_paper.grid(row=0, column=0, sticky="news")
        self.select_all.grid(row=0, column=1, sticky="news")
        #
        self.paper_title.grid(row=0, column=0, columnspan=4, sticky="nwe")
        self.paper_authors.grid(row=1, column=0, columnspan=4, sticky="nwe")
        self.inspire_id.grid(row=2, column=0, sticky="sw")
        self.arxiv_abs.grid(row=2, column=1, sticky="se")
        self.arxiv_pdf.grid(row=2, column=2, sticky="swe")
        self.get_bibtex.grid(row=2, column=3, sticky="swe")
        self.text_box.grid(row=3, column=0, sticky="news")
        self.bibentry.grid(row=4, column=0, columnspan=4, sticky="news")
        self.status_bar.grid(row=6, column=0, columnspan=4, sticky="news")
        # self.dropdown_set.grid(row = 3, column = 1, columnspan = 2, sticky = "news")
        self.update_paper.grid(row=3, column=3, sticky="news")

        # For the tabbing order
        self.text_box.lift()
        self.bibentry.lift()

        # For redirecting stdout to the label status_bar
        class StandardOut():
            """Redirect standard output to the tooltip in the status bar below"""

            def __init__(self, obj, master, label):
                self.stream = obj
                self.master = master
                self.label = label
                self.grand_total = ""
                self.tooltip = CreateToolTip(master, label,
                                             text="The history of the messages caps at 18 lines or 800 characters.")

            def write(self, text):
                # This also writes on the terminal
                # sys.__stdout__.write(text)
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
                self.tooltip = CreateToolTip(self.master, self.label, text=self.grand_total[:-1])

            def flush(self):
                pass

        class StandardErr():
            """Redirect standard err to a log file with datestamps"""

            def __init__(self, path):
                self.path = os.path.dirname(os.path.realpath(__file__)) + "/" + path
                self.last_write = datetime(1999, 1, 1)

            def write(self, text):
                with open(self.path, "a") as f:
                    n = datetime.now()
                    if (n - self.last_write).total_seconds() > 60:
                        print("An error occurred, see error.log (click here).")
                        f.write(datetime.now().strftime('[%a %d-%m-%Y %H:%M:%S]\n'))
                        self.last_write = datetime.now()
                    f.write(text)

            def flush(self):
                pass

        # sys.stdout = StandardOut(self.status, self.master, self.status_bar)
        # sys.stderr = StandardErr('error.log')

        # If the default file or given file exists, load it
        try:
            with open(self.default_filename, "r", encoding="utf-8") as file:
                contents = file.read()
                self.biblio.parse(contents)
                # Drop down menus
                self.create_menus()
                self.load_data()
                # This makes the scrollbar start at the bottom at the initial loading
                self.paper_list.scrollbar.set(1.0, 1.0)
                for c in self.paper_list.column_dict:
                    self.paper_list.column_dict[c].list_box.yview_moveto(1.0)
        except FileNotFoundError:
            if len(self.sysargv) > 1:
                print(f"The file {self.sysargv[1]} is not available.")
            else:
                print("The default file is not available.")
            self.create_menus()
            self.on_new_file()

        # Finally we load the new papers from the arxiv and load them in a new file
        def has_saved(*args):
            print('New papers obtained and saved in .arxiv_new.txt')

        def didnt_need_to_save(*args):
            print('New papers obtained from file .arxiv_new.txt')

        self.newQuery = Query()
        self.newQuery.list_papers(self.def_cat.get(), 0, didnt_need_to_save, has_saved)

    def on_keyboard_interrupt(self):
        """When Ctrl+C has been pressed"""
        self.interrupt_process = True

    def max_characters(self):
        """Returns the maximal number of characters fitting on the right frame"""
        return self.frame_right.winfo_width() // 9

    def create_menus(self):
        """Creates the dropdown menus for filtering and selecting the paper category and also the one for exporting"""
        # For mapping the entries in the dict to the way they look in the menu
        if hasattr(self, "category_dict"):
            self.category_dict.update(self.biblio.cat_dict)
        else:
            self.category_dict = self.biblio.cat_dict
        self.category_dict_inv = {v: k for k, v in self.category_dict.items()}

        # Drop down menu for editing the paper category
        self.categories = ["All"] + list(self.category_dict.values())
        self.dropdown_set_val = StringVar()
        self.dropdown_set_val.set(self.categories[0])
        self.current_category = []
        self.dropdown_set = OptionMenu(self.frame_right, self.dropdown_set_val, *self.categories)
        self.dropdown_set.children["menu"].add_separator()
        self.dropdown_set.children["menu"].add_command(label="Choose more", command=self.on_change_flags_other)
        self.dropdown_set.config(font=self.listfont, width=11)
        self.dropdown_set_val.trace_id = self.dropdown_set_val.trace("w", self.on_change_flags)

        # Drop down menu for filtering the paper category
        self.dropdown_filter_val = StringVar()
        self.dropdown_filter_val.set(self.categories[0])
        self.dropdown_filter = OptionMenu(self.frame_left, self.dropdown_filter_val, command=self.on_filter,
                                          *self.categories)
        self.dropdown_filter.children["menu"].add_separator()
        self.dropdown_filter.children["menu"].add_command(label="Locally saved PDFs", command=self.on_filter_forpdf)
        self.dropdown_filter.config(font=self.listfont)

        self.export.menus_already_there = []
        # Drop down menu for the export
        self.export.delete(4, self.export.index("end"))
        for cat in self.categories[1:]:
            self.export.add_command(label=cat, command=self.export_group(cat))
            self.export.menus_already_there.append(cat)

        # I have to grid them here
        self.dropdown_filter.grid(row=0, column=2, columnspan=2, sticky="news")
        self.dropdown_set.grid(row=3, column=1, columnspan=2, sticky="news")

    def export_group(self, cat):
        """Exports to a file only the papers that belong to a given group"""
        flag = self.category_dict_inv[cat]

        def f():
            filename = filedialog.asksaveasfilename(initialdir=self.current_folder(), title="Select file",
                                                    filetypes=(("BibTeX files", "*.bib"), ("All files", "*.*")))
            if not filename:
                print("No file selected. I did not do anything.")
                return
            try:
                with open(filename, "w+", encoding="utf-8") as file:
                    for key, entry in self.biblio.entries.items():
                        if flag in entry.flags:
                            file.write(entry.write())

            except (PermissionError, TypeError, FileNotFoundError) as e:
                print("Error occurred when saving file.")

        return f

    def export_selected(self, mode):
        """Exports to a file only the papers given in a selection"""

        def f():
            sel = self.paper_list.curselection()
            entries = [self.biblio.entries[self.paper_list.get(a)[0]] for a in sel]
            filename = filedialog.asksaveasfilename(initialdir=self.current_folder(), title="Select file",
                                                    filetypes=(("BibTeX files", "*.bib"), ("All files", "*.*")))
            if not filename:
                print("No file selected. I did not do anything.")
                return
            if len(entries) == 0:
                print("There were no selected papers.")
                return False
            try:
                with open(filename, f"{mode}+", encoding="utf-8") as file:
                    for entry in entries:
                        file.write(entry.write())

            except (PermissionError, TypeError, FileNotFoundError) as e:
                print("Error occurred when saving file.")

        return f

    def export_from_bbl(self):
        """Exports the bibliography items found in a .bbl file"""

        filename = filedialog.askopenfilename(initialdir=self.current_folder(), title="Select file",
                                                filetypes=(("Bibliography files", "*.bbl"), ("All files", "*.*")))
        if not filename:
            print("No file selected. I did not do anything.")
            return

        try:
            with open(filename, "r", encoding="utf-8") as file:
                contents = file.read()
        except (PermissionError, TypeError, FileNotFoundError) as e:
            print("Error occurred when opening file.")

        bibitem_list = re.finditer(r"\\bibitem\{([^}{]+)\}", contents)

        default_bibentry = """@article{{{},
    author = "Found, Not",
    title = "{{Not Found}}",
    eprint = "xxxx.xxxxx",
    archivePrefix = "arXiv",
    primaryClass = "hep-th"
}}"""

        not_found_entries = []

        def default_item(name):
            not_found_entries.append(name)

            return biblioDB.Bibentry(
                title = "Not found",
                arxiv_no = "xxxx.xxxxx",
                inspire_id = name,
                bibentry = default_bibentry.format(name),
                authors = [("Not", "Found")],
                initials = "NF"
            )

        current_export = []
        for item_matchobj in bibitem_list:
            item = item_matchobj.group(1)
            to_export = self.biblio.entries.get(item, None)
            if to_export is None:
                to_export = default_item(item)
            current_export.append(to_export)

        filename = filedialog.asksaveasfilename(initialdir=self.current_folder(), title="Select file",
                                                filetypes=(("BibTeX files", "*.bib"), ("All files", "*.*")))
        if not filename:
            print("No file selected. I did not do anything.")
            return
        try:
            with open(filename, f"w+", encoding="utf-8") as file:
                for entry in current_export:
                    file.write(entry.write())

        except (PermissionError, TypeError, FileNotFoundError) as e:
            print("Error occurred when saving file.")
            return

        if not_found_entries:
            not_found_string = ', '.join(not_found_entries)
            print('Some entries could not be found: ' + not_found_string)


    def on_status_bar_click(self, event):
        if self.status.get() == "An error occurred, see error.log (click here).":
            errorfile = os.path.join(os.path.dirname(__file__), "error.log")
            if os.name == 'nt':
                # Not tested yet
                os.system(f"cmd /C 'more {errorfile}'")
            else:
                os.system(f"{self.default_terminal} bash -c 'less {errorfile}'")
        else:
            return

    def see_bibfile(self):
        if os.name == 'nt':
            # Not tested yet
            os.system(f"cmd /C \"more {self.current_file}\"")
        else:
            os.system(f"{self.default_terminal} bash -c 'less {self.current_file}'")

    def right_click_popup(self, event):
        try:
            self.popup_menu.post(event.x_root, event.y_root)
        finally:
            self.popup_menu.grab_release()

    def toggle_arxiv_add(self, event=None):
        """Toggles whether the Arxiv number prompt pops up after pressing Add or not"""
        self.ask_arxiv_on_add = not self.ask_arxiv_on_add
        self.add_paper.configure(text="Add" if self.ask_arxiv_on_add else "Add (no prompt)")

    def exit_popup(self, event):
        """Kills menu in the bibentry widget"""
        self.popup_menu.unpost()

    def enable_menu(self):
        """Shows menu in the bibentry widget"""
        if self.bibentry.tag_ranges(SEL):
            self.popup_menu.entryconfig(0, state=NORMAL)
            self.popup_menu.entryconfig(1, state=NORMAL)
            self.popup_menu.entryconfig(4, state=NORMAL)
            self.popup_menu.entryconfig(5, state=NORMAL)
        else:
            self.popup_menu.entryconfig(0, state=DISABLED)
            self.popup_menu.entryconfig(1, state=DISABLED)
            self.popup_menu.entryconfig(4, state=DISABLED)
            self.popup_menu.entryconfig(5, state=DISABLED)

    def on_cut(self):
        """Cut button on the Menu on the bibentry widget"""
        ranges = self.bibentry.tag_ranges(SEL)
        text = self.bibentry.get(*ranges)
        self.master.clipboard_clear()
        self.master.clipboard_append(text)
        text = text.replace("\n", "")
        maxchar = self.max_characters() - 20
        if len(text) > maxchar:
            text = text[0:maxchar // 2] + "..." + text[-maxchar // 2:]
        print(text + " copied to clipboard")
        self.bibentry.delete(*ranges)

    def on_copy(self):
        """Copy button on the Menu on the bibentry widget"""
        ranges = self.bibentry.tag_ranges(SEL)
        text = self.bibentry.get(*ranges)
        self.master.clipboard_clear()
        self.master.clipboard_append(text)
        text = text.replace("\n", "")
        maxchar = self.max_characters() - 20
        if len(text) > maxchar:
            text = text[0:maxchar // 2] + "..." + text[-maxchar // 2:]
        print(text + " copied to clipboard")

    def on_indent(self):
        """Indent button on the Menu on the bibentry widget"""
        indentation = 4
        ranges = self.bibentry.tag_ranges(SEL)
        ranges = self.bibentry.index(ranges[0]) + "linestart", self.bibentry.index(ranges[1])
        text = self.bibentry.get(*ranges)
        text = indentation * " " + text.replace("\n", "\n" + indentation * " ")
        self.bibentry.delete(*ranges)
        self.bibentry.insert(ranges[0], text)

    def on_deindent(self):
        """De-indent button on the Menu on the bibentry widget"""
        indentation = 4
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

    def custom_paste(self, event=None):
        """Custom paste method that overwrites the selected text"""
        # Courtesy of https://stackoverflow.com/a/46636970
        if event is None:
            widget = self.bibentry
        else:
            widget = event.widget
        try:
            text = self.master.clipboard_get()
        except:
            return "break"
        try:
            widget.delete("sel.first", "sel.last")
        except:
            pass
        widget.insert(INSERT, text)
        return "break"

    def adjust_wraplength(self, event=None):
        """Readjust wraplength on resize"""
        w = event.width if event is not None else self.master.winfo_width()
        self.paper_title.adjust_wraplength(w)
        self.paper_authors.adjust_wraplength(w)

    def copy_to_clipboard(self, event=None):
        """Copies the inspire_id text to the system clipboard"""
        self.master.clipboard_clear()
        self.master.clipboard_append(self.inspire_text.get())
        print(self.inspire_text.get() + " copied to clipboard")

    def current_folder(self):
        """Simply returns the folder containing self.current_file"""
        if self.current_file == None:
            return os.path.expanduser('~')
        else:
            return os.path.dirname(self.current_file)

    def disable_buttons(self):
        """The two buttons start as disabled at every load.
           Enable them once and make this function trivial when called again"""
        self.get_bibtex.config(state=DISABLED)
        self.update_paper.config(state=DISABLED)
        self.dropdown_set.config(state=DISABLED)
        self.editmenu.entryconfig(2, state=DISABLED)
        self.editmenu.entryconfig(3, state=DISABLED)

        def g():
            self.dropdown_set.config(state=NORMAL)
            self.update_paper.config(state=NORMAL)
            self.editmenu.entryconfig(2, state=NORMAL)
            self.get_bibtex.config(state=NORMAL)
            self.editmenu.entryconfig(3, state=NORMAL)

            def f():
                pass

            self.enable_buttons = f

        self.enable_buttons = g

    def on_esc_press(self, event):
        if event.widget in [w.list_box for w in self.paper_list.column_dict.values()]:
            self.disable_buttons()
            self.current_pdf_path = ""

    def count_papers(self):
        print("There are currently {} papers.".format(len(self.biblio.entries.keys())))

    def load_data(self):
        """Loads the data on the listbox"""
        self.paper_list.delete(0, END)
        self.disable_buttons()
        self.current_pdf_path = ""

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

            # Grid the local pdf label if needed
            if entry.local_pdf != "":
                self.local_pdf_label.grid(row=5, column=0, columnspan=4, sticky="news")
                maxchar = self.max_characters() - 13
                if len(entry.local_pdf) > maxchar:
                    shortened = entry.local_pdf[0:maxchar // 2] + "..." + entry.local_pdf[-maxchar // 2:]
                else:
                    shortened = entry.local_pdf
                if os.path.isfile(self.full_path(entry.local_pdf)):
                    self.local_pdf_label.config(fg="#000000")
                    self.local_pdf_str.set("Local pdf in " + shortened)
                    self.current_pdf_path = entry.local_pdf
                    self.pdfmenu.entryconfig(1, state=NORMAL)
                else:
                    self.local_pdf_label.config(fg="#cc0000")
                    self.local_pdf_str.set("Local pdf in " + shortened + " unavailable!")
                    self.current_pdf_path = ""
                    self.pdfmenu.entryconfig(1, state=DISABLED)
            else:
                self.local_pdf_label.grid_forget()
                self.current_pdf_path = ""
                self.pdfmenu.entryconfig(1, state=DISABLED)

            # Here I temporarily suppress the callback to put the dropdown menu on Multiple groups
            self.dropdown_set_val.trace_vdelete("w", self.dropdown_set_val.trace_id)
            if len(entry.flags) == 1:
                self.dropdown_set_val.set(self.category_dict.get(entry.flags[0], "Group not found"))
            elif len(entry.flags) == 0:
                self.dropdown_set_val.set("All")
            else:
                self.dropdown_set_val.set("Multiple groups")
            self.dropdown_set_val.trace_id = self.dropdown_set_val.trace("w", self.on_change_flags)
            # Then I set the flags
            self.current_category = entry.flags

            # Writes the authors and binds links to them
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

            self.local_pdf_label.grid_forget()
            self.current_pdf_path = ""

            # Here I temporarily suppress the callback to put the dropdown menu on All
            self.dropdown_set_val.trace_vdelete("w", self.dropdown_set_val.trace_id)
            self.dropdown_set_val.set("All")
            self.current_category = None
            self.dropdown_set_val.trace_id = self.dropdown_set_val.trace("w", self.on_change_flags)

            # Writes the authors and binds links to them, only if they are less than 10
            all_authors = []
            maxauthors = 10
            for e in entries:
                all_authors += [a for a in e.authors if a not in all_authors]
            all_authors.sort(key=lambda x: x[1])
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
            self.bibentry.config(fg="gray35")
            # Ok, this is kind of weird, but I have a check that makes the color back to black only if there is something bound to <1>
            self.bibentry.binding = self.bibentry.bind("<1>", lambda x: None)
            if self.overwrite_flags:
                line1 = "overwrites instead of adding"
            else:
                line1 = "adds instead of overwriting"
            self.bibentry.insert(1.0, f"Changing the groups from the \"Choose more\" menu {line1}.\n\n"
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

    def on_arxiv_pdf(self, online_override=False):
        """Event: load arxiv PDF page or the local copy if exists"""

        def f():

            if self.current_pdf_path != "" and os.path.isfile(
                    self.full_path(self.current_pdf_path)) and not online_override:
                if self.full_path(self.current_pdf_path).split(".")[-1] == "pdf":
                    subprocess.Popen([self.pdf_viewer[0], self.full_path(self.current_pdf_path)])
                else:
                    subprocess.Popen([self.pdf_viewer[1], self.full_path(self.current_pdf_path)])
            else:
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
            # link = simpledialog.askstring(title="Preprint number",
            #                              prompt="Insert here the preprint number:")
            d = Arxiv_prompt(self,
                             lambda done: self.newQuery.list_papers(self.def_cat.get(), self.request_verbosity, done))
            self.master.wait_window(d.choose)
            link = d.response
            if link is None or link == "":
                print("I did not do anything.")
                return None
        if self.arxiv_link.get() == "Multiple links":
            self.update_all()
        else:
            try:
                text = Query.get(link, self.request_verbosity)
            except Query.PaperNotFound:
                return None
            else:
                self.remove_info()
                self.bibentry.insert(1.0, text)

    def on_change_flags_other(self, *args):
        """Event called when a new value from the selection dropdown menu is changed and 'Choose more' has been selected"""
        # Insert here the call to a new window for selecting the categories
        s = Category_Selection(self, self.current_category)
        self.master.wait_window(s.sel)
        response = s.response

        self.biblio.cat_dict.update(response)
        self.current_category = []
        for a in list(response.keys()):
            self.current_category.append(a)

        # Here I do part of the things done in create_menu(). I do not recall it to avoid recursion
        self.category_dict = self.biblio.cat_dict
        self.category_dict_inv = {v: k for k, v in self.category_dict.items()}
        self.categories = list(self.category_dict.values())

        self.dropdown_set_val.trace_vdelete("w", self.dropdown_set_val.trace_id)
        if len(self.current_category) == 0:
            self.dropdown_set_val.set("All")
        elif len(self.current_category) == 1:
            self.dropdown_set_val.set(self.category_dict[self.current_category[0]])
        else:
            self.dropdown_set_val.set("Multiple groups")
        self.dropdown_set = OptionMenu(self.frame_right, self.dropdown_set_val, *self.categories)
        self.dropdown_set.children["menu"].add_separator()
        self.dropdown_set.children["menu"].add_command(label="Choose more", command=self.on_change_flags_other)
        self.dropdown_filter = OptionMenu(self.frame_left, self.dropdown_filter_val, command=self.on_filter,
                                          *self.categories)
        self.dropdown_filter.children["menu"].add_separator()
        self.dropdown_filter.children["menu"].add_command(label="Locally saved PDFs", command=self.on_filter_forpdf)
        self.dropdown_set_val.trace_id = self.dropdown_set_val.trace("w", self.on_change_flags)

        self.dropdown_set.config(font=self.listfont, width=11)
        self.dropdown_filter.config(font=self.listfont)

        # Adding the groups to the export menu
        for cat in self.categories[1:]:
            if not cat in self.export.menus_already_there:
                self.export.add_command(label=cat, command=self.export_group(cat))
                self.export.menus_already_there.append(cat)

        # I have to grid them here
        self.dropdown_filter.grid(row=0, column=2, columnspan=2, sticky="news")
        self.dropdown_set.grid(row=3, column=1, columnspan=2, sticky="news")

    def on_change_flags(self, *args):
        """Event called when a new value from the selection dropdown menu is changed and it's not 'Choose more'"""
        self.current_category = self.category_dict_inv[self.dropdown_set_val.get()]

    def on_update(self):
        """Event: the button "Update" has been pressed"""
        bib = self.bibentry.get(1.0, END)
        com = self.comment.get().replace("|", " ").replace("}", " ").replace("}", " ")
        locpdf = self.current_pdf_path
        flag = self.current_category
        sel = self.paper_list.curselection()
        ent = self.inspire_text.get()
        remember_bib = self.biblio.entries[ent].bibentry if not ent == "<id>" else ""

        if len(sel) <= 1:
            # Modify or add only one paper
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
                    self.biblio.comment_entries[ent].update({"description": com, "category": flag, "local_pdf": locpdf})
                else:
                    self.biblio.comment_entries.update(
                        {ent: {"description": com, "category": flag, "local_pdf": locpdf}})

                entry = self.biblio.entries[ent]
                self.biblio.link_comment_entry(entry)
                self.paper_list.insert(sel, entry.inspire_id, entry.initials, entry.description)
                self.paper_list.selection_set(sel)
                self.list_has_changed((sel,))
                for c in self.paper_list.column_dict:
                    self.paper_list.column_dict[c].list_box.see(sel)

        elif flag is not None:
            # Modify the flags of a group of papers
            entlist = [self.paper_list.get(s)[0] for s in sel]

            def merge(str1, str2):
                if self.overwrite_flags:
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
                    # The flags are added to the existing ones or overwritten.
                    # It depends on the value of the global variable overwrite_flags
                    self.biblio.comment_entries[en].update({"category": merge(iniflag, flag)})
                else:
                    self.biblio.comment_entries.update(
                        {en: {"description": "Not found", "category": flag, "local_pdf": ""}})
                entry = self.biblio.entries[en]
                self.biblio.link_comment_entry(entry)
            if flag == "":
                if self.overwrite_flags:
                    print(f"The group(s) have been cleared from {len(sel)} entries.")
                else:
                    print("I did not do anything.")
            else:
                flaglong = ",".join([self.category_dict[a] for a in flag])
                grp, has = ("", "s") if len(flag) == 1 else ("s", "ve")
                added = "assigned" if self.overwrite_flags else "added"
                print(f"The group{grp} {flaglong} ha{has} been {added} to {len(sel)} entries.")
        else:
            print("I did not do anything.")
            return 0

        self.is_modified = True
        if self.current_file == None:
            self.master.title("*Bibliography - Untitled")
        else:
            self.master.title("*Bibliography - " + self.current_file.split("/")[-1])

    def remove_info(self, event=None):
        """If the info message in grey is showing in the text box removes that and reverts the configuration, otherwise just erases the textbox."""
        if self.bibentry.binding is not None:
            self.bibentry.unbind("<1>", self.bibentry.binding)
            self.bibentry.config(fg='#ffffff' if int(self.frame_right.cget('bg').replace('#','0x'),16) < 8388607 else '#000000')
        self.bibentry.delete(1.0, END)
        self.bibentry.binding = None

    def on_add(self):
        """Add an item"""
        self.paper_list.selection_clear(0, END)

        self.bibentry.delete(1.0, END)
        self.bibentry.insert(1.0,
                             "%%Click on \"Get Bibtex\" to insert the ArXiv number and load the Bibtex entry or type the Bibtex entry here.%%" +
                             "\n\n@article{Author:2020abc,\n"
                             "         ...\n"
                             "}")
        self.bibentry.config(fg='gray60' if int(self.frame_right.cget('bg').replace('#','0x'),16) < 8388607 else 'gray35')
        self.bibentry.binding = self.bibentry.bind("<1>", self.remove_info)

        self.comment.set("Insert description here.")
        self.inspire_text.set("<id>")
        self.paper_title.text_set("Title")
        self.paper_authors.text_set("Authors")
        self.arxiv_link.set("n/a")
        self.dropdown_set_val.set(self.category_dict[""])

        self.local_pdf_label.grid_forget()
        self.current_pdf_path = ""

        self.enable_buttons()
        if self.ask_arxiv_on_add:
            self.on_get_bibtex()

    def on_select_all(self):
        """Selects all papers"""
        self.paper_list.selection_set(0, END)

    def on_remove(self):
        """Remove an item"""
        sel = self.paper_list.curselection()
        if len(sel) > 0:
            entries = [(s, self.paper_list.get(s)[0]) for s in sel]
            for s, ent in sorted(entries, key=lambda x: x[0], reverse=True):
                del self.biblio.entries[ent]
                self.paper_list.delete(s)

            self.paper_list.selection_clear(0, END)
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
                self.master.title("*Bibliography - Untitled")
            else:
                self.master.title("*Bibliography - " + self.current_file.split("/")[-1])
            self.disable_buttons()

    def on_search(self, event=None):
        """Search for a pattern"""
        self.dropdown_filter_val.set("Search results")
        sstring = self.search_string.get()
        hist = self.search_box.search_history
        if not hist or not sstring == hist[-1]:
            hist.append(sstring)
        query = self.biblio.parse_search(self.search_string.get())
        self.biblio.filter(query)
        self.load_data()

    def on_history_up(self, event=None):
        if self.search_box.history_count < len(self.search_box.search_history):
            self.search_box.history_count += 1
            if self.search_box.history_count == 1:
                self.search_box.temp = self.search_string.get()
            self.search_string.set(self.search_box.search_history[-self.search_box.history_count])
            self.search_box.icursor(END)

    def on_history_down(self, event=None):
        if self.search_box.history_count == 1:
            self.search_string.set(self.search_box.temp)
            self.search_box.history_count = 0
        elif self.search_box.history_count > 1:
            self.search_box.history_count -= 1
            self.search_string.set(self.search_box.search_history[-self.search_box.history_count])
        self.search_box.icursor(END)

    def on_exit_search(self, event=None):
        """Closes the search"""
        self.dropdown_filter_val.set("All")
        self.on_filter()

    def on_menu_search(self, event=None):
        """Shows the search widgets and focuses on the search textbox"""
        self.search_box.focus_set()
        self.search_box.grid(row=2, column=0, columnspan=2, sticky="news")
        self.search_button.grid(row=2, column=2, columnspan=2, sticky="news")

        self.search_box.bind("<Return>", self.on_search)
        self.search_box.bind("<Escape>", self.on_exit_search)
        self.search_box.bind("<Up>", self.on_history_up)
        self.search_box.bind("<Down>", self.on_history_down)

    def on_filter(self, event=None):
        """The filter dropdown menu has changed"""
        self.tooltip.hidetip(self.master)
        self.search_box.grid_forget()
        self.search_string.set("")
        self.search_box.history_count = 0
        self.search_button.grid_forget()

        self.search_box.unbind("<Return>")
        self.search_box.unbind("<Escape>")
        self.search_box.unbind("<Up>")
        self.search_box.unbind("<Down>")

        flag = self.category_dict_inv.get(self.dropdown_filter_val.get(), None)
        if flag is None:
            if self.dropdown_filter_val.get() == "All":
                for e in self.biblio.entries.values():
                    e.visible = True
            else:
                for e in self.biblio.entries.values():
                    e.visible = False
        else:
            for e in self.biblio.entries.values():
                if flag in e.flags:
                    e.visible = True
                else:
                    e.visible = False

        self.load_data()

    def on_filter_forpdf(self, event=None):
        """The filter dropdown menu has changed"""
        self.tooltip.hidetip(self.master)
        self.search_box.grid_forget()
        self.search_string.set("")
        self.search_box.history_count = 0
        self.search_button.grid_forget()

        for e in self.biblio.entries.values():
            if e.local_pdf:
                e.visible = True
            else:
                e.visible = False

        self.dropdown_filter_val.set("Locally saved PDFs")
        self.load_data()

    def on_sort_date(self):
        """Sorts by date"""
        self.biblio.sort_by(lambda x: x.date)
        self.load_data()

        self.paper_list.scrollbar.set(1.0, 1.0)
        for c in self.paper_list.column_dict:
            self.paper_list.column_dict[c].list_box.yview_moveto(1.0)

        self.is_modified = True
        if self.current_file == None:
            self.master.title("*Bibliography - Untitled")
        else:
            self.master.title("*Bibliography - " + self.current_file.split("/")[-1])

    def on_sort_title(self):
        """Sorts by title"""
        self.biblio.sort_by(lambda x: x.title)
        self.load_data()

        self.paper_list.scrollbar.set(1.0, 1.0)
        for c in self.paper_list.column_dict:
            self.paper_list.column_dict[c].list_box.yview_moveto(1.0)

        self.is_modified = True
        if self.current_file == None:
            self.master.title("*Bibliography - Untitled")
        else:
            self.master.title("*Bibliography - " + self.current_file.split("/")[-1])

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

        self.interrupt_process = False
        for el in entries:
            if self.interrupt_process:
                sys.stdout.flush()
                print("\nUpdating process interrupted by keyboard")
                break
            if el.arxiv_no not in ["n/a", ""]:
                animation += 1
                try:
                    text = Query.get(el.arxiv_no, self.request_verbosity)
                    if el.bibentry != text:
                        count += 1
                        old_inspire_id = self.biblio.get_id(el.bibentry)
                        new_inspire_id = self.biblio.get_id(text)
                        if old_inspire_id == new_inspire_id:
                            el.bibentry = text
                        else:
                            self.biblio.entries[new_inspire_id] = self.biblio.entries[old_inspire_id].copy()
                            self.biblio.entries[new_inspire_id].bibentry = text
                            self.biblio.entries[new_inspire_id].inspire_id = new_inspire_id
                            self.biblio.comment_entries[new_inspire_id] = self.biblio.comment_entries[
                                old_inspire_id].copy()
                            self.biblio.link_comment_entry(self.biblio.entries[new_inspire_id])
                            del self.biblio.entries[old_inspire_id]
                            del self.biblio.comment_entries[old_inspire_id]

                except Query.PaperNotFound:
                    sys.stdout.flush()
                else:
                    # This is just an animation to show that the program is not frozen
                    sys.stdout.write("\rFetching data from Inspire...{}".format(["|", "/", "-", "\\"][animation % 4]))
                    sys.stdout.flush()

        if count == 1:
            print("Updated 1 entry.")
        else:
            print("Updated {} entries.".format(count))
        if count > 0:
            self.is_modified = True
            if self.current_file == None:
                self.master.title("*Bibliography - Untitled")
            else:
                self.master.title("*Bibliography - " + self.current_file.split("/")[-1])
            if self.paper_list.curselection() != ():
                sel = self.paper_list.curselection()
                self.load_data()
                [self.paper_list.selection_set(ee) for ee in sel]
                self.list_has_changed(self.paper_list.curselection())
                for c in self.paper_list.column_dict:
                    self.paper_list.column_dict[c].list_box.see(sel[-1])

    def on_new_file(self):
        """Creates a new file"""
        if self.is_modified:
            if not messagebox.askokcancel("New filed?", "The last modifications will be discarded."):
                return
        self.biblio.entries = {}
        self.biblio.comment_entries = {}
        self.biblio.cat_dict = {"": "All", "r": "To read"}
        self.category_dict = {}
        self.create_menus()
        self.load_data()
        self.current_file = None

        self.is_modified = False
        self.master.title("Bibliography - Untitled")

    def on_open_file(self):
        """Opens a .bib file with comments compatible with this application. Discards current state of the biblio"""
        if self.is_modified:
            if not messagebox.askokcancel("Open?", "The last modifications will be discarded."):
                return
        filename = filedialog.askopenfilename(initialdir=self.current_folder(), title="Select file",
                                              filetypes=(("BibTeX files", "*.bib"), ("All files", "*.*")))
        if not filename:
            print("No file selected.")
            return
        try:
            with open(filename, "r", encoding="utf-8") as file:
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
                self.master.title("Bibliography - " + filename.split("/")[-1])
        except (FileNotFoundError, TypeError) as e:
            print("Error occurred when loading file.")

    def on_open_file_merge(self):
        """Opens a .bib file with comments compatible with this application. Merges the content of the current biblio"""
        if self.is_modified:
            if not messagebox.askokcancel("Open?", "The last modifications will be discarded."):
                return
        filename = filedialog.askopenfilename(initialdir=self.current_folder(), title="Select file",
                                              filetypes=(("BibTeX files", "*.bib"), ("All files", "*.*")))
        if not filename:
            print("No file selected.")
            return
        try:
            with open(filename, "r", encoding="utf-8") as file:
                save_cat_dict = self.biblio.cat_dict.copy()
                save_comments = copy.deepcopy(self.biblio.comment_entries)

                contents = file.read()
                self.biblio.parse(contents)
                save_cat_dict.update(self.biblio.cat_dict)
                save_comments.update(self.biblio.comment_entries)
                self.biblio.cat_dict = save_cat_dict.copy()
                self.biblio.comment_entries = copy.deepcopy(save_comments)

                # Now we link the comment lines to the bib entries
                for e in self.biblio.entries.values():
                    self.biblio.link_comment_entry(e)

                self.create_menus()
                self.load_data()

                self.current_file = filename
                self.is_modified = True
                self.master.title("*Bibliography - " + filename.split("/")[-1])
        except (FileNotFoundError, TypeError) as e:
            print("Error occurred when loading file.")

    def on_save_file(self):
        """Saves a .bib file with comments compatible with this application."""
        filename = filedialog.asksaveasfilename(initialdir=self.current_folder(), title="Select file",
                                                filetypes=(("BibTeX files", "*.bib"), ("All files", "*.*")))
        if not filename:
            print("No file selected. I did not do anything.")
            return
        try:
            with open(filename, "w+", encoding="utf-8") as file:
                file.write(self.biblio.comment_string())
                for key, entry in self.biblio.entries.items():
                    file.write(entry.write())

                self.current_file = filename
                self.is_modified = False
                self.master.title("Bibliography - " + filename.split("/")[-1])
        except (PermissionError, TypeError, FileNotFoundError) as e:
            print("Error occurred when saving file.")

    def on_save_this_file(self):
        """Saves a .bib file with comments compatible with this application. Saves on the current file"""
        if self.current_file == None:
            self.on_save_file()
        else:
            try:
                with open(self.current_file, "w+", encoding="utf-8") as file:
                    file.write(self.biblio.comment_string())
                    for key, entry in self.biblio.entries.items():
                        file.write(entry.write())

                    self.is_modified = False
                    self.master.title("Bibliography - " + self.current_file.split("/")[-1])
            except PermissionError:
                print("Error occurred when saving file.")

    def on_save_nocomments(self):
        """Saves a .bib file without the comments. Saves on the current file"""
        if self.current_file == None:
            filename = filedialog.asksaveasfilename(initialdir=self.current_folder(), title="Select file",
                                                    filetypes=(("BibTeX files", "*.bib"), ("All files", "*.*")))
        else:
            filename = self.current_file
        sel = self.paper_list.curselection()
        entries = self.biblio.entries.values()
        if not filename:
            print("No file selected. I did not do anything.")
            return
        try:
            with open(filename, "w+", encoding="utf-8") as file:
                for entry in entries:
                    file.write(entry.write())
            print("The file was exported in place.")

        except (PermissionError, TypeError, FileNotFoundError) as e:
            print("Error occurred when exporting file in place.")

    def make_relative(self, path):
        """Makes a path relative with respect to the current bibtex file"""
        return os.path.relpath(path, start=self.current_folder())

    def make_absolute(self, path):
        """Makes a path absolute"""
        return os.path.realpath(path)

    def full_path(self, path):
        """Makes a relative path absolute with respect to the current folder"""
        if self.linked_pdf_relative:
            return self.current_folder() + "/" + path
        else:
            return path

    def on_link_pdf(self):
        """Links a paper to a locally stored pdf file"""
        if len(self.paper_list.curselection()) != 1:
            return None
        filename = filedialog.askopenfilename(initialdir=self.default_pdf_path, title="Select file",
                                              filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")))
        if not filename:
            print("No file selected. I did not do anything.")
            return None
        if self.linked_pdf_relative:
            filename = self.make_relative(filename)
        else:
            filename = self.make_absolute(filename)
        if os.path.isfile(self.full_path(filename)):
            self.current_pdf_path = filename
            self.on_update()
        else:
            print("The specified file does not exist.")

    def on_unlink_pdf(self):
        """Unlinks a paper to its locally stored pdf file"""
        if len(self.paper_list.curselection()) != 1:
            return None
        self.current_pdf_path = ""
        self.on_update()

    def on_save_pdf(self):
        """Saves a pdf locally and links it"""
        if len(self.paper_list.curselection()) != 1:
            return None
        if self.arxiv_link.get() != "n/a":
            filename = filedialog.asksaveasfilename(initialdir=self.default_pdf_path, title="Select file",
                                                    filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")))
            if not filename:
                print("No file selected. I did not do anything.")
                return None
            if self.linked_pdf_relative:
                filename = self.make_relative(filename)
            else:
                filename = self.make_absolute(filename)
            url = "https://arxiv.org/pdf/{}.pdf"
            self.current_pdf_path = filename
            print("Downloading...")
            urllib.request.urlretrieve(url.format(self.arxiv_link.get()), self.full_path(filename))
            self.on_update()
            self.on_arxiv_pdf()()
        else:
            print("ArXiv number not available. Cannot save on file.")

    def on_close(self):
        """Closes the main window"""
        if self.is_modified:
            if messagebox.askokcancel("Quit?", "The last modifications will be discarded."):
                self.master.destroy()
                self.master.quit()
        else:
            self.master.destroy()
            self.master.quit()
