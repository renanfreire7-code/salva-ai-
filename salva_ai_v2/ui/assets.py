from pathlib import Path
from math import ceil
import tkinter as tk
import base64


def load_asset(master,name,max_size):
    data=(Path(__file__).resolve().parents[1]/'assets'/name).read_bytes()
    source=tk.PhotoImage(master=master,data=base64.b64encode(data),format='png')
    factor=max(1,ceil(max(source.width(),source.height())/max_size))
    return source.subsample(factor,factor)
