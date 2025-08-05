import sqlite3
from tkinter import *

class DB:
    def __init__(self):
        self.conn = sqlite3.connect('C:/Users/almei/PycharmProjects/banco_compostos/compounds.db')
        self.cur = self.conn.cursor()
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS tbl_compound (
                compound_id INTEGER PRIMARY KEY,
                compound TEXT,
                molecular_formula TEXT,
                molecular_mass REAL
            )
        ''')
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS tbl_matrixes (
                matrixes_id INTEGER PRIMARY KEY,
                organism TEXT,
                plant_tissue TEXT
            )
        ''')
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS tbl_name (
                name_id INTEGER PRIMARY KEY,
                name TEXT
            )
        ''')
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS tbl_identification (
                identification_id INTEGER PRIMARY KEY,
                compound_id INTEGER,
                matrix_id INTEGER,
                name_id INTEGER,
                FOREIGN KEY (compound_id) REFERENCES tbl_compound(compound_id),
                FOREIGN KEY (matrix_id) REFERENCES tbl_matrixes(matrixes_id),
                FOREIGN KEY (name_id) REFERENCES tbl_name(name_id)
            )
        ''')


        self.conn.commit()

    def __del__(self):
        self.conn.close()

    def view_compound(self):
        self.cur.execute("SELECT * FROM tbl_compound")
        rows = self.cur.fetchall()
        return rows

    def view_matrixes(self):
        self.cur.execute("SELECT * FROM tbl_matrixes")
        rows = self.cur.fetchall()
        return rows

    def view_names(self):
        self.cur.execute("SELECT * FROM tbl_name")
        rows = self.cur.fetchall()
        return rows

    def view_identification(self):
        self.cur.execute("SELECT * FROM tbl_identification")
        rows = self.cur.fetchall()
        return rows

    def insert_compound(self, compound, molecular_formula, molecular_mass):
        self.cur.execute("INSERT INTO tbl_compound (compound, molecular_formula, molecular_mass) VALUES (?, ?, ?)",
                         (compound, molecular_formula, molecular_mass))
        self.conn.commit()

    def insert_matrix(self, organism, plant_tissue):
        self.cur.execute("INSERT INTO tbl_matrixes (organism, plant_tissue) VALUES (?, ?)",
                         (organism, plant_tissue))
        self.conn.commit()

    def insert_name(self, name):
        self.cur.execute("INSERT INTO tbl_name (name) VALUES (?)", (name,))
        self.conn.commit()

    def insert_identification(self, compound_id, matrix_id, name_id):
        self.cur.execute("INSERT INTO tbl_identification (compound_id,matrix_id,name_id) VALUES (?, ?, ?)")
        self.conn.commit()

db = DB()

def get_selected_row(event):
    global selected_tuple
    index = list1.curselection()[0]
    selected_tuple = list1.get(index)
    e1.delete(0, END)
    e1.insert(END, selected_tuple[1])
    e2.delete(0, END)
    e2.insert(END, selected_tuple[2])
    e3.delete(0, END)
    e3.insert(END, selected_tuple[3])

def view_compound_command():
    compound_frame.grid(row=2, column=0)
    organism_frame.grid_forget()
    name_frame.grid_forget()
    list1.delete(0, END)
    for row in db.view_compound():
        list1.insert(END, row)

def view_matrixes_command():
    organism_frame.grid(row=2, column=0)
    compound_frame.grid_forget()
    name_frame.grid_forget()
    list1.delete(0, END)
    for row in db.view_matrixes():
        list1.insert(END, row)

def view_names_command():
    name_frame.grid(row=2, column=0)
    compound_frame.grid_forget()
    organism_frame.grid_forget()
    list1.delete(0, END)
    for row in db.view_names():
        list1.insert(END, row)

def view_identifications_command():
    identification_frame.grid(row=2, column=0)
    compound_frame.grid_forget()
    organism_frame.grid_forget()
    name_frame.grid_forget()
    list1.delete(0, END)
    for row in db.view_identification():
        list1.insert(END, row)


def add_compound_command():
    db.insert_compound(compound_text.get(), molecular_formula_text.get(), molecular_mass_text.get())
    e1.delete(0, END)
    e2.delete(0, END)
    e3.delete(0, END)
    view_compound_command()

def add_matrix_command():
    db.insert_matrix(organism_text.get(), plant_tissue_text.get())
    e4.delete(0, END)
    e5.delete(0, END)

def add_name_command():
    db.insert_name(name_text.get())
    e6.delete(0, END)

def add_identification_command():
    db.insert_identification(compound_id_text.get(), matrix_id_text.get(), name_id_text.get())
    e7.delete(0, END)
    e8.delete(0, END)
    e9.delete(0, END)


window = Tk()
window.title("Compounds Database")
window.geometry("700x400")  # Define o tamanho da janela

compound_frame = Frame(window)
organism_frame = Frame(window)
name_frame = Frame(window)
identification_frame = Frame(window)

l1 = Label(compound_frame, text="Compound")
l1.grid(row=0, column=0)

l2 = Label(compound_frame, text="Molecular Formula")
l2.grid(row=0, column=2)

l3 = Label(compound_frame, text="Molecular Mass")
l3.grid(row=1, column=0)

compound_text = StringVar()
e1 = Entry(compound_frame, textvariable=compound_text)
e1.grid(row=0, column=1)

molecular_formula_text = StringVar()
e2 = Entry(compound_frame, textvariable=molecular_formula_text)
e2.grid(row=0, column=3)

molecular_mass_text = StringVar()
e3 = Entry(compound_frame, textvariable=molecular_mass_text)
e3.grid(row=1, column=1)

l4 = Label(organism_frame, text="Organism")
l4.grid(row=0, column=0)

l5 = Label(organism_frame, text="Plant Tissue")
l5.grid(row=0, column=2)

organism_text = StringVar()
e4 = Entry(organism_frame, textvariable=organism_text)
e4.grid(row=0, column=1)

plant_tissue_text = StringVar()
e5 = Entry(organism_frame, textvariable=plant_tissue_text)
e5.grid(row=0, column=3)

l6 = Label(name_frame, text="Name")
l6.grid(row=0, column=0)

name_text = StringVar()
e6 = Entry(name_frame, textvariable=name_text)
e6.grid(row=0, column=1)

l7 = Label(identification_frame, text="Compound ID")
l7.grid(row=0, column=0)

l8 = Label(identification_frame, text="Matrix ID")
l8.grid(row=0, column=2)

l9 = Label(identification_frame, text="Name ID")
l9.grid(row=0, column=4)

compound_id_text = StringVar()
e7 = Entry(identification_frame, textvariable=compound_id_text)
e7.grid(row=0, column=1)

matrix_id_text = StringVar()
e8 = Entry(identification_frame, textvariable=matrix_id_text)
e8.grid(row=0, column=3)

name_id_text = StringVar()
e9 = Entry(identification_frame, textvariable=name_id_text)
e9.grid(row=0, column=5)


list1 = Listbox(window, height=10, width=65)
list1.grid(row=3, column=0, rowspan=6, columnspan=2)

sb1 = Scrollbar(window)
sb1.grid(row=3, column=2, rowspan=6)

list1.configure(yscrollcommand=sb1.set)
sb1.configure(command=list1.yview)

list1.bind('<<ListboxSelect>>', get_selected_row)

b1 = Button(window, text="View Compounds", width=12, command=view_compound_command)
b1.grid(row=3, column=3)

b2 = Button(window, text="Add Compound", width=12, command=add_compound_command)
b2.grid(row=4, column=3)

b3 = Button(window, text="View Matrixes", width=12, command=view_matrixes_command)
b3.grid(row=5, column=3)

b4 = Button(window, text="Add Matrix", width=12, command=add_matrix_command)
b4.grid(row=6, column=3)

b5 = Button(window, text="View Names", width=12, command=view_names_command)
b5.grid(row=7, column=3)

b6 = Button(window, text="Add Name", width=12, command=add_name_command)
b6.grid(row=8, column=3)

b7 = Button(window, text="View Identifications", width=15, command=view_identifications_command)
b7.grid(row=7, column=3)

b8 = Button(window, text="Add Identification", width=15, command=add_identification_command)
b8.grid(row=8, column=3)



view_compound_command()

window.mainloop()