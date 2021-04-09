from tkinter import *
from tkinter import font
import webbrowser
import re, itertools
import sympy as sp
from PIL import Image, ImageTk
from io import BytesIO
import os
import threading


class MultiListbox(Frame):
    """This is the widget of a ListBox with more columns"""
    def __init__(self, master, **kwargs):
        self.master = master
        self.frame = Frame(master)
        self.paned = PanedWindow(self.frame)
        self.paned.config(sashrelief = FLAT, sashwidth = 2, relief = SUNKEN)
        self.scrollbar = Scrollbar(self.frame)

        #Fake label
        self.fake = Frame(self.frame, height = 35, width = 1)
        
        #Grid things inside the frame
        self.frame.columnconfigure(0, weight = 1)
        self.frame.columnconfigure(1, weight = 0)
        self.frame.rowconfigure(0, weight = 0)
        self.frame.rowconfigure(1, weight = 1)
        self.paned.grid(row = 0, column = 0, rowspan = 2, sticky = "news")
        self.fake.grid(row = 0, column = 1, sticky = "ns")
        self.scrollbar.grid(row = 1, column = 1, sticky = "news")

        self.column_dict = {}
        self.columns = ()
        self.callback = (lambda x: None)

        #Polling for selection
        self.poll()
        
        self.config(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def config(self, **kwargs):
        """Configures the multiListBox. If given the columns options it creates them, otherwise configs all the present ones"""
        self.columns  = kwargs.get("columns", self.columns)
        inherited_kwargs = {i : kwargs[i] for i in kwargs if i not in
                            ("columns", "selectcmd", "columnfont")}
        colfont = kwargs.get("columnfont", (None, 12))
        if "selectmode" not in inherited_kwargs.keys():
            inherited_kwargs["selectmode"] = EXTENDED
        if "columns" in kwargs.keys():
            for c in self.columns:
                self.create_column(c, colfont, **inherited_kwargs)
        else:
            for c in self.columns:
                self.column_dict[c].list_box.config(**inherited_kwargs)

        #Scrollbar configuration (thanks to https://stackoverflow.com/a/11337277)
        def all_yview(*args):
            for c in self.column_dict:
                self.column_dict[c].list_box.yview(*args)

        def yscoll_column(column):
            def f(*args):
                for c in [x for x in self.column_dict if x is not column]:
                    a = self.column_dict[c].list_box
                    b = self.column_dict[column].list_box
                    if a.yview() != b.yview():
                        a.yview_moveto(args[0])
                    self.scrollbar.set(*args)
            return f 

        for c in self.column_dict:
            self.column_dict[c].list_box.config(yscrollcommand = yscoll_column(c))
        
        self.scrollbar.config(command = all_yview)

        #Defines the callback for selection
        self.callback = kwargs.get("selectcmd", self.callback)

    def create_column(self, name, columnfont, **kwargs):
        """Creates a new column with header"""
        new_frame = Frame(self.paned)
        self.column_dict.update({name : new_frame})
        self.paned.add(new_frame)
        new_frame.list_box = Listbox(new_frame)
        new_frame.list_box.config(**kwargs, exportselection = 0)
        new_frame.top = Button(new_frame)
        new_frame.top.config(font = columnfont, relief = RAISED, text = name)

        new_frame.list_box.current_selection = ()

        #Grid all
        new_frame.columnconfigure(0, weight = 1)
        new_frame.rowconfigure(0, weight = 0)
        new_frame.rowconfigure(1, weight = 1)
        new_frame.top.grid(row = 0, column = 0, sticky = "nwe")
        new_frame.list_box.grid(row = 1, column = 0, sticky = "news")

    class ColumnNotExistent(Exception):
        pass

    def bind_command(self, columname, command):
        """Binds a command to the column with name columname"""
        if columname in list(self.column_dict):
            col = self.column_dict[columname]
        else:
            raise self.ColumnNotExistent("Column " + columname + " does not exist.")

        col.top.config(command = command)
        

    def set_widths(self, *args):
        """Set the witdths of the columns by placing the first n-1 sashes"""
        self.paned.update()
        cumulative = 0
        for i in range(len(args)):
            cumulative += args[i]
            self.paned.sash_place(i, cumulative, 1)

    def poll(self):
        """Polls for selection and syncronizes"""
        for c in self.column_dict:
            cc = self.column_dict[c].list_box
            if cc.current_selection != cc.curselection():
                cursel = cc.curselection()
                for b in self.column_dict:
                    bb = self.column_dict[b].list_box
                    bb.current_selection = cursel
                    bb.selection_clear(0, END)
                    [bb.selection_set(i) for i in cursel]
                self.callback(cursel)
                        
        self.master.after(10, self.poll)

    def insert(self, index, *args):
        i = 0
        for c in self.column_dict:
            self.column_dict[c].list_box.insert(index, args[i])
            i+=1

    def get(self, index, end = None):
        ret = []
        for c in self.column_dict:
            cc = self.column_dict[c].list_box
            ret.append(cc.get(index, end))

        return ret

    def curselection(self):
        c = self.column_dict[self.columns[0]].list_box
        return c.curselection()

    def delete(self, first, last = None):
        for c in self.column_dict:
            cc = self.column_dict[c].list_box
            cc.delete(first, last)

    def selection_set(self, first, last = None):
        for c in self.column_dict:
            cc = self.column_dict[c].list_box
            cc.selection_set(first, last)

    def selection_clear(self, first, last = None):
        for c in self.column_dict:
            cc = self.column_dict[c].list_box
            cc.selection_clear(first, last)


class ToolTip(object):
    """Creates an hovering tooltip to explain properties of a widget"""
    #From https://stackoverflow.com/a/56749167
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.schedule = None

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 57
        y = y + cy + self.widget.winfo_rooty() +27
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        exp_height = (text.count("\n") + 3)* 17
        tw.wm_geometry("+%d+%d" % (x, y - exp_height))
        label = Label(tw, text=self.text, justify=LEFT,
                      fg='#000000', bg="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("DejaVu Sans", "10", "normal"))
        label.pack(ipadx=1)

    def showtip_delayed(self, parent, text, delay):
        self.schedule = parent.after(delay, self.showtip, text)

    def hidetip(self, parent):
        tw = self.tipwindow
        self.tipwindow = None
        #This cancels the scheduled event for showing the tooltip
        if self.schedule is not None:
            parent.after_cancel(self.schedule)
        if tw:
            tw.destroy()

def CreateToolTip(parent, widget, text, delay = 1500):
    """Creates a tooltop with a given text hovering above the cursore"""
    toolTip = ToolTip(widget)
    def enter(event):
           toolTip.showtip_delayed(parent, text, delay)
    def leave(event):
        toolTip.hidetip(parent)
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)
    return toolTip

class HyperrefText(Text):
    """Class inherited from Text that can display hyperlinks"""
    def text_set(self, text):
        """Sets text"""
        self.config(state = NORMAL)
        for tag in self.tag_names():
            self.tag_delete(tag)
        self.delete(1.0, END)
        self.insert(1.0, text)
        self.config(state = DISABLED)

    def text_add(self, text):
        """Appends text"""
        self.config(state = NORMAL)
        self.insert(END, text)
        self.config(state = DISABLED)

    def underline(self, tag):
        """Underlines the link text"""
        def f(event = None):
            self.config(cursor = "hand1")
            self.tag_config(tag, underline = 1)
        return f

    def deunderline(self, tag):
        """De-underlines the link text"""
        def f(event = None):
            self.config(cursor = "arrow")
            self.tag_config(tag, underline = 0)
        return f

    def callback(self, url):
        """Opens the search on Inspire for the authors"""
        def f(event = None):
            webbrowser.open_new_tab(url)
        return f

    def link_add(self, text, url):
        """Adds a link to the text"""
        cursor_bef = self.index('end-1c')
        self.text_add(text)
        cursor_aft = self.index('end-1c')
        self.tag_add(text, cursor_bef, cursor_aft)
        if int(self.cget('bg').replace('#','0x'),16) < 8388607:
            self.tag_config(text, foreground="maroon1")
        else:
            self.tag_config(text, foreground = "blue")
        self.tag_bind(text, "<1>", self.callback(url))
        self.tag_bind(text, "<Enter>", self.underline(text))
        self.tag_bind(text, "<Leave>", self.deunderline(text))

    def adjust_wraplength(self, w):
        #Thanks to the great Bryan Oakley https://stackoverflow.com/a/46100295
        height = self.tk.call((self._w, "count", "-update", "-displaylines", "1.0", "end"))
        self.configure(height = height)

class LatexText(HyperrefText):
    """Class inherited from HyperrefText that can parse and render LaTeX"""
    latex_delay = 100
    
    def __init__(self, *args, **kwargs):
        self.schedule = []
        self.pictures = {}
        HyperrefText.__init__(self, *args, **kwargs)
    
    def latex_set(self, text):
        """Sets text by parsing \href as hyperlinks and $...$ as LaTeX code"""
        #Cancel all scheduled LaTeX renderings in order to do these
        for task in self.schedule:
            self.master.after_cancel(task)
        self.schedule = []
        self.pictures = {}

        self.config(state = NORMAL)
        self.delete(1.0, END)

        #Keep track of the $...$
        texts  = []
        latexs = []
        previous_mark = 0
        matches_inline = re.finditer(r"(\$.+?\$)|(\\href{.*}{.*})", text)
        for match in matches_inline:
            latexs.append(match.group(0))
            texts.append(text[previous_mark:match.start(0)])
            previous_mark = match.end(0)
        texts.append(text[previous_mark:])

        #Adds the portions of text subdivided before
        for i, t in enumerate(itertools.zip_longest(texts, latexs, fillvalue = "")):
            self.insert(END, t[0])
            # start = self.index("end-1c")
            href = re.match(r"\\href{(.*)}{(.*)}", t[1])
            if href:
                self.link_add(href.group(2), href.group(1))
                self.config(state = NORMAL)
            elif len(t[1]) > 0:
                self.insert(END, t[1], str(i))
                self.tag_configure(str(i), foreground = "#6000bf")
                self.schedule_latex(t[1], tag=str(i), tot=len(latexs))

        self.config(state = DISABLED)

    def schedule_latex(self, string, tag, tot):
        """Schedules a latex rendering and adds the task to the list schedule"""
        #I put a small delay but probably this is not needed anymore with this new method
        task = self.master.after(self.latex_delay, self.render_latex, string, tag, tot)
        self.schedule.append(task)

    def render_latex(self, *args):
        """Renders a portion of text in LaTeX as a picture and attaches it to the widged"""
        def funct(text=None, tag=None, tot=None):
            if text is None or tag is None:
                print("Ignoring")
                return
            #This creates a ByteIO stream and saves there the output of sympy.preview
            f = BytesIO()
            if os.name == "nt":
                rgb = self.master.winfo_rgb(self.master.cget('bg'))
                rgb = rgb[0]//256, rgb[1]//256, rgb[2]//256
                the_color = "{%x%x%x}" % rgb
                the_color = the_color.upper()
            else:
                the_color = "{" + self.master.cget('bg')[1:].upper()+"}"
            if int('0x'+the_color.strip('{}'), 16) < 8388607:
                fg_color = '{ffffff}'
            else:
                fg_color = '{000000}'
            #The raisebox is to prevent the image cropping and to center it
            sp.preview(r"$\displaystyle\phantom{\raisebox{1mm}{|}}\!\!\!\!\!\!$\textcolor{fg}{"+text+"}", euler = False,
            preamble = r"\documentclass{standalone}"
                       r"\usepackage{pagecolor}"
                       r"\usepackage{amsmath}"
                       r"\usepackage{amssymb}"
                       r"\usepackage{amsfonts}"
                       r"\definecolor{graybg}{HTML}" + the_color +
                       r"\definecolor{fg}{HTML}" + fg_color +
                       r"\pagecolor{graybg}"
                       r"\begin{document}",
                       viewer = "BytesIO", output = "ps", outputbuffer=f)
            f.seek(0)
            #Open the image as if it were a file. This works only for .ps!
            img = Image.open(f)
            #You can also put scale = 3 and remove the next line
            img.load(scale = 6)
            img = img.resize((int(img.size[0]/2),int(img.size[1]/2)),Image.BILINEAR)
            self.pictures.update({tag: (ImageTk.PhotoImage(img), text)})
            f.close()

            #Call the function if everything is done
            if set(self.pictures.keys()) == set([str(a) for a in range(tot)]):
                self.put_pictures()


        proc = threading.Thread(target = funct, args = args)
        proc.start()

    def put_pictures(self):
        """Puts the images in the text box"""

        #Now we can put the image in the text
        self.config(state = NORMAL)
        for tag in self.pictures:
            try:
                start, end = self.tag_ranges(tag)
            except:
                return
            #This checks whether the text has changed in the meantime
            img = self.pictures[tag][0]
            text = self.pictures[tag][1]
            if self.get(start, end) != text:
                return
            self.delete(start, end)
            self.image_create(start, image = img)
            self.mark_unset(start)
            self.mark_unset(end)

        

class Arxiv_prompt():
    """Shows a messagebox prompting the ArXiv number and listing new papers"""
    def __init__(self, parent, function):
        self.function = function
        self.response = ""
        choose = self.choose = Toplevel(parent.master)
        self.parent = parent
        choose.wm_title(string = "Preprint number")
        wx = parent.master.winfo_rootx()
        wy = parent.master.winfo_rooty()
        choose.geometry("380x120+%d+%d" % (wx+100, wy+100))
        choose.protocol("WM_DELETE_WINDOW", self.on_cancel)
        choose.label1 = Label(choose, anchor = "c", text = "Insert here the preprint number:",
                             font = (None, 12))
        choose.label2 = Button(choose, anchor = "c", text = "Or choose one of the new papers",
                             font = (None, 12), command = self.fill_papers, width = 30)
        choose.ok = Button(choose, text = "Ok", command = self.on_close, font = (None, 12))
        choose.cancel = Button(choose, text = "Cancel", command = self.on_cancel, font = (None, 12))
        
        choose.papers = MultiListbox(choose)
        choose.papers.config(columns = ("Inspire ID", "Title"), font = self.parent.listfont,
                             selectcmd = self.selected, columnfont = (None, 11),
                             bg='white' if int(self.parent.frame_right.cget('bg').replace('#','0x'),16) > 8388607 else '#222222')
        choose.papers.config(selectmode = BROWSE)
        choose.papers.set_widths(110)

        self.responseVar = StringVar()
        choose.text = Entry(choose, textvariable = self.responseVar, font = (None, 12), relief = SUNKEN, width = 32,
                            bg='white' if int(self.parent.frame_right.cget('bg').replace('#','0x'),16) > 8388607 else '#222222')
        choose.text.bind("<Return>", lambda x: self.on_close())

        #Grid everything
        choose.columnconfigure(0, weight = 1)
        choose.columnconfigure(1, weight = 1)
        choose.rowconfigure(4, weight = 0)
        choose.rowconfigure(3, weight = 1)
        choose.label1.grid(column = 0, row = 0, columnspan = 2)
        choose.text.grid(column = 0, row = 1, columnspan = 2)
        choose.label2.grid(column = 0, row = 2, columnspan = 2)
        choose.ok.grid(column = 0, row = 4, sticky = "wes")
        choose.cancel.grid(column = 1, row = 4, sticky = "wes")

        #This ensures that the parent window cannot be interacted with
        choose.grab_set()
        
    def fill_papers(self):
        """Puts the papers in the MultiListbox from the Arxiv API"""
        self.choose.papers.grid(column = 0, row = 3, columnspan = 2, sticky = "news")
        wh = self.choose.winfo_height()
        ww = self.choose.winfo_width()
        self.choose.geometry("%dx%d" % (max(800, ww), max(400, wh)))

        def done(instance):
            paper_dict = instance.contents
            print("New papers obtained")
            self.choose.papers.delete(0, END)
            for aid, title in paper_dict.items():
                self.choose.papers.insert(END, aid, title)

        print("Fetching new papers...")
        self.function(done)


    def selected(self, selection):
        """A paper has been selected"""
        sel = self.choose.papers.get(selection[0])[0]
        self.responseVar.set(sel)

    def on_cancel(self):
        """Cancel has been pressed"""
        self.response = ""
        self.choose.destroy()

    def on_close(self):
        """Ok has been pressed"""
        self.response = self.responseVar.get()
        self.choose.destroy()


class Category_Selection():
    """A window that allows the user to choose for the category where to put the paper"""
    def __init__(self, parent, current):        
        self.response = {}
        sel = self.sel = Toplevel(parent.master)
        self.parent = parent
        self.current = current
        if self.current is None:
            self.current = ""
        sel.wm_title(string = "Classify paper")
        wx = parent.master.winfo_rootx()
        wy = parent.master.winfo_rooty()
        if os.name == "nt":
            sel.geometry("600x560+%d+%d" % (wx+100, wy+100))
        else:
            sel.geometry("600x520+%d+%d" % (wx+100, wy+100))
        sel.protocol("WM_DELETE_WINDOW", self.on_cancel)

        sel.ok = Button(sel, text = "Ok", command = self.on_close, font = (None, 12))
        sel.cancel = Button(sel, text = "Cancel", command = self.on_cancel, font = (None, 12))
        sel.label = Label(sel, text = "\nCheck the groups to which you want to add this paper.\nDefine a name for newly created groups.\n")
        sel.label.configure(font = (None, 12), width = 50)
        sel.none = Button(sel, text = "Deselect all", command = self.on_deselect, font = (None, 12))

        letters = self.letters = {}
        for col in (0,1):
            for l in ("acegikmoqsuwy", "bdfhjlnprtvxz")[col]:
                v = IntVar()
                DEJAVUSANSMONO = "Lucida Sans Typewriter" if os.name == "nt" else "DejaVu Sans Mono"
                the_check = Checkbutton(sel, text = l, variable = v, font = (DEJAVUSANSMONO, 13))
                the_check.var = v
                the_string = StringVar()
                the_entry = Entry(sel, textvariable = the_string, font = (None, 12), relief = SUNKEN, width = 20,
                                  bg='white' if int(self.parent.frame_right.cget('bg').replace('#','0x'),16) > 8388607 else '#222222')
                the_string.trace("w", self.restore_color(the_entry))
                the_entry.string = the_string
                if l in parent.biblio.cat_dict.keys():
                    the_string.set(parent.biblio.cat_dict[l])
                if l in self.current:
                    v.set(1)
                letters[l] = {"check" : the_check, "entry" : the_entry, "col" : 2*col}

        #Grid everything
        sel.columnconfigure(0, weight = 0)
        sel.columnconfigure(1, weight = 1)
        sel.columnconfigure(2, weight = 0)
        sel.columnconfigure(3, weight = 1)
        sel.label.grid(column = 0, row = 0, sticky = "wen", columnspan = 4)
        sel.none.grid(column = 1, row = 1, sticky = "nsw")

        row = 1
        for l in letters.values():
            row += 1
            l["check"].grid(column = l["col"], row = row-13*l["col"]//2, sticky = "ne")
            l["entry"].grid(column = l["col"]+1, row = row-13*l["col"]//2, sticky = "nw")

        sel.ok.grid(column = 0, row = row+1, sticky = "nwes", columnspan = 2)
        sel.cancel.grid(column = 2, row = row+1, sticky = "nwes", columnspan = 2)

        sel.rowconfigure(row, weight = 1)
        sel.rowconfigure(row+1, weight = 0)

        #This ensures that the parent window cannot be interacted with
        sel.grab_set()

    def restore_color(self, obj):
        """Restores the color to black"""
        def f(*event):
            obj.configure(fg = "black")
        return f

    def on_deselect(self):
        """Deselect all"""
        for l in self.letters.values():
            l["check"].var.set(0)

    def duplicate_free_q(self):
        sofar = []
        ret = True
        for l in self.letters.values():
            s = l["entry"].string.get()
            if not s == "":
                if s in sofar:
                    ret = False
                    l["entry"].configure(fg = "red2")
                sofar.append(s)
        return ret

    def non_empty_q(self):
        ret = True
        for l in self.letters.values():
            if l["entry"].string.get() == "" and l["check"].var.get() == 1:
               l["entry"].string.set("Unnamed group")
               l["entry"].configure(fg = "red2")
               ret = False
        return ret

    def on_close(self):
        """Ok has been pressed"""
        c1 = self.duplicate_free_q()
        c2 = self.non_empty_q()
        if c1 and c2:
            self.response = {}
            for l in self.letters:
                if self.letters[l]["check"].var.get() == 1:
                    self.response[l] = self.letters[l]["entry"].string.get()
            self.sel.destroy()

    def on_cancel(self):
        """Cancel has been pressed"""
        self.response = {l:self.parent.biblio.cat_dict[l] for l in self.current}
        self.sel.destroy()

"""
#Try it out!
if __name__ == "__main__":
    def changed(selection):
        try:
            sel = selection[0]
        except:
            sel = 0
        print("{} - {} - {}".format(*mlb.get(sel)))

    master = Tk()
    mlb = MultiListbox(master)
    mlb.config(columns = ("col1", "col2", "?"), font = ("DejaVu Sans Mono", 12),
               columnfont = ("DejaVu Sans Mono", 12), selectmode = SINGLE, selectcmd = changed)

    master.columnconfigure(0, weight = 1)
    master.rowconfigure(0, weight = 1)
    mlb.grid(row = 0, column = 0, sticky = "news")

    for item in range(50):
        mlb.insert(END, str(item) + " ehi","Asd " + str(50-item), "NOOO" + str(item * 10))

    master.mainloop()
"""
