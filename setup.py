#!/usr/bin/env python
from __future__ import absolute_import
import re
from setuptools import setup, find_packages
import json

if __name__ == '__main__':
    with open('setup.json', 'r') as info:
        kwargs = json.load(info)
    setup(
        include_package_data=True,
        reentry_register=True,
	zip_safe = True,
        packages=find_packages(
            where='.', exclude=("yambo.*", "parser.*", "yambo*", "parser*")),
        **kwargs)
    #import reentry
    #reentry.manager.scan()
    
