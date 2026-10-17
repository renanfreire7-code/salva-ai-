from .assets import load_asset

APP_NAME='Bar Simples'


def load_logo(master,max_size):
    return load_asset(master,'bar_simples_logo.png',max_size)


def load_icon(master,max_size):
    return load_asset(master,'bar_simples_icon.png',max_size)
