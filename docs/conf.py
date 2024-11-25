# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

import datetime

# -- Project information -----------------------------------------------------

project = "Ubuntu Pro Client"
author = "Canonical Group Ltd"
copyright = "%s, %s" % (datetime.date.today().year, author)
# If your project is on documentation.ubuntu.com, specify the project
# slug (for example, "lxd") here.
slug = ""

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    "myst_parser",
    "notfound.extension",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinxcontrib.mermaid",
    "sphinx.ext.autosectionlabel",
    "sphinxcontrib.jquery",
    "sphinxext.opengraph",
    "sphinxext.rediraffe",
]
autosectionlabel_prefix_document = True

# Add any paths that contain templates here, relative to this directory.

templates_path = ["_templates"]

html_extra_path = ["googleaf254801a5285c31.html", "sitemap-index.xml"]

# Add redirects, so they can be updated here to land with docs being moved
rediraffe_branch = "docs"
rediraffe_redirects = "redirects.txt"


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.

exclude_patterns = []

# It seems we need to request creation of automatic anchors for our headings.
# Setting to 2 because that's what we need now.
# If referencing any heading of lesser importance, adjust here.

myst_heading_anchors = 3


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes:
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
# html_logo = "_static/circle_of_friends.png"
html_theme_options = {
    "light_css_variables": {
        "color-sidebar-background-border": "none",
        "font-stack": "Ubuntu, -apple-system, Segoe UI, Roboto, Oxygen, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif",
        "font-stack--monospace": "Ubuntu Mono variable, Ubuntu Mono, Consolas, Monaco, Courier, monospace",
        "color-foreground-primary": "#111",
        "color-foreground-secondary": "var(--color-foreground-primary)",
        "color-foreground-muted": "#333",
        "color-background-secondary": "#FFF",
        "color-background-hover": "#f2f2f2",
        "color-brand-primary": "#111",
        "color-brand-content": "#06C",
        "color-inline-code-background": "rgba(0,0,0,.03)",
        "color-sidebar-link-text": "#111",
        "color-sidebar-item-background--current": "#ebebeb",
        "color-sidebar-item-background--hover": "#f2f2f2",
        "sidebar-item-line-height": "1.3rem",
        "color-link-underline": "var(--color-background-primary)",
        "color-link-underline--hover": "var(--color-background-primary)",
    },
    "dark_css_variables": {
        "color-foreground-secondary": "var(--color-foreground-primary)",
        "color-foreground-muted": "#CDCDCD",
        "color-background-secondary": "var(--color-background-primary)",
        "color-background-hover": "#666",
        "color-brand-primary": "#fff",
        "color-brand-content": "#06C",
        "color-sidebar-link-text": "#f7f7f7",
        "color-sidebar-item-background--current": "#666",
        "color-sidebar-item-background--hover": "#333",
    },
}
html_context = {
    "product_page": "ubuntu.com/pro",
    "product_tag": "_static/circle_of_friends.png",
    "github_version": "docs",
    "github_folder": "/docs/",
    "github_issues": "enabled"
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_css_files = [
    "css/logo.css",
    "css/github_issue_links.css",
    "css/custom.css",
    "css/mermaid.css",
    "css/header.css",
    "css/furo_colors.css",
    "css/highlight.css",
]
html_js_files = [
    "js/github_issue_links.js",
    "js/header-nav.js",
    "js/synced_tab_links.js",
]
html_favicon = "_static/favicon.ico"


linkcheck_ignore = [
    "https://manpages.ubuntu.com/landscape-config",
    "https://manpages.ubuntu.com/apt.conf"
]


ogp_site_url = 'https://canonical-ubuntu-pro-client.readthedocs-hosted.com/'
ogp_site_name = project
ogp_image = 'https://assets.ubuntu.com/v1/253da317-image-document-ubuntudocs.svg'

# The default for notfound_urls_prefix usually works, but not for
# documentation on documentation.ubuntu.com
if slug:
    notfound_urls_prefix = '/' + slug + '/en/latest/'

notfound_context = {
    'title': 'Page not found',
    'body': '<h1>Page not found</h1>\n\n<p>Sorry, but the documentation page that you are looking for was not found.</p>\n<p>Documentation changes over time, and pages are moved around. We try to redirect you to the updated content where possible, but unfortunately, that didn\'t work this time (maybe because the content you were looking for does not exist in this version of the documentation).</p>\n<p>You can try to use the navigation to locate the content you\'re looking for, or search for a similar page.</p>\n',
}

copybutton_exclude = '.linenos, .gp'
