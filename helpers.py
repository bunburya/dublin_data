#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from configparser import ConfigParser
from os.path import join, expanduser
from time import localtime, strftime

def get_config(conf_file=None):
    
    conf_file = conf_file or expanduser('~/.config/dublin_data.ini')
    config = ConfigParser()
    config.optionxform = lambda option: option
    config.read(conf_file)
    return config

def timestamp(data):
    data['timestamp'] = localtime()
    data['timestamp_str'] = strftime('%H:%M:%S on %A %d %B %Y')
    return data
