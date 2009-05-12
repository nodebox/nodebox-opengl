import os
from distutils.core import setup

# Dynamically calculate the version based on nodebox.VERSION.
version = __import__('nodebox').get_version()

packages = [
    'nodebox',
    'nodebox.graphics',
    'nodebox.gui']

setup(
    name = "NodeBox",
    version = version.replace(' ', '-'),
    url = 'http://www.nodebox.net/',
    author = 'Frederik De Bleser, Tom De Smedt',
    description = 'A Python framework that lets you create interactive 2D visuals using OpenGL.',
    packages = packages,
)