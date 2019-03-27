from tkinter import *
import tkinter.font

import sys

from cozmorosie import *
from PySoarLib import LanguageConnector

class ChatGUI(Frame):
    def __init__(self, soar_agent, master=None):
        Frame.__init__(self, master, width=800, height=600)
        self.soar_agent = soar_agent

        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        self.message_history = []
        self.history_index = 0

        self.create_widgets()
        self.create_script_buttons()

        self.language_connector = LanguageConnector(soar_agent)
        self.language_connector.register_message_callback(self.receive_message)
        soar_agent.add_connector("language", self.language_connector)

    def create_widgets(self):
        self.grid(row=0, column=0, sticky=N+S+E+W)
        self.columnconfigure(0, weight=3, minsize=600)
        self.columnconfigure(1, weight=1, minsize=400)
        self.columnconfigure(2, weight=1, minsize=100)
        self.rowconfigure(0, weight=10, minsize=400)
        self.rowconfigure(1, weight=1, minsize=50)

        self.messages_list = Listbox(self, font=("Times", "12"))
        self.scrollbar = Scrollbar(self.messages_list)
        self.messages_list.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.messages_list.yview)
        self.messages_list.grid(row=0, column=0, sticky=N+S+E+W)
        self.scrollbar.pack(side=RIGHT, fill=Y)

        self.script_frame = Frame(self)
        self.script_frame.grid(row=0, column=1, sticky=N+S+E+W)

        self.chat_entry = Entry(self, font=("Times", "16"))
        self.chat_entry.bind('<Return>', lambda key: self.on_submit_click())
        self.chat_entry.bind('<Up>', lambda key: self.scroll_history(-1))
        self.chat_entry.bind('<Down>', lambda key: self.scroll_history(1))
        self.chat_entry.grid(row=1, column=0, sticky=N+S+E+W)

        self.submit_button = Button(self, text="Send", font=("Times", "24"))
        self.submit_button["command"] = self.on_submit_click
        self.submit_button.grid(row=1, column=1, sticky=N+S+E+W)

        self.run_button = Button(self, text="Run", font=("Times", "24"))
        self.run_button["command"] = self.on_run_click
        self.run_button.grid(row=1, column=2, sticky=N+S+E+W)

    def create_script_buttons(self):
        self.script = []
        if self.soar_agent.messages_file != None:
            with open(self.soar_agent.messages_file, 'r') as f:
                self.script = [ line.rstrip('\n') for line in f.readlines() if len(line.rstrip('\n')) > 0 and line[0] != '#']

        row = 0
        for message in self.script:
            button = Button(self.script_frame, text=message[:30], font=("Times", "16"))
            button["command"] = lambda message=message: self.send_message(message)
            button.grid(row=row, column=0, sticky=N+S+E+W)
            row += 1

    def send_message(self, message):
        self.messages_list.insert(END, message)
        self.chat_entry.delete(0, END)
        if len(self.message_history) == 0 or self.message_history[-1] != message:
            self.message_history.append(message)
        self.history_index = len(self.message_history)
        self.language_connector.send_message(message)

    def receive_message(self, message):
        self.messages_list.insert(END, "Rosie: " + message)

    def on_submit_click(self):
        self.send_message(self.chat_entry.get())
        
    def on_run_click(self):
        self.soar_agent.start()

    def scroll_history(self, delta):
        if self.history_index == 0 and delta == -1:
            return
        if self.history_index == len(self.message_history) and delta == 1:
            return

        self.history_index += delta
        self.chat_entry.delete(0, END)
        if self.history_index < len(self.message_history):
            self.chat_entry.insert(END, self.message_history[self.history_index])

