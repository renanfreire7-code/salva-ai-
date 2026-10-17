from pathlib import Path
from math import ceil
import tkinter as tk


def load_asset(master,name,max_size):
    source=tk.PhotoImage(master=master,file=str(Path(__file__).resolve().parents[1]/'assets'/name))
    factor=max(1,ceil(max(source.width(),source.height())/max_size))
    return source.subsample(factor,factor)
