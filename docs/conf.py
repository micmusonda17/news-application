"""Sphinx build configuration for the News Application documentation.

Because this is a Django project, Sphinx has to set up Django before it
can import any of the models. That is what the DJANGO_SETTINGS_MODULE
line and django.setup() below are for. USE_SQLITE is set so that the
documentation can be built without a MariaDB server running.
"""

import os
import sys

import django

# Let Sphinx see the project folder that sits above this docs folder.
sys.path.insert(0, os.path.abspath('..'))

# Django has to be configured before autodoc imports the models.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'news_project.settings')
os.environ.setdefault('USE_SQLITE', 'True')
django.setup()


# -- Project information -----------------------------------------------------

project = 'News Application'
copyright = '2026, Michael Musonda'
author = 'Michael Musonda'
release = '00.00.01'


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'en'


# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
