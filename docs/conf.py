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
#
# The canonical_sphinx extension provides the shared Canonical theme and
# automatically loads a set of common extensions when they are installed,
# including: myst_parser, sphinx_design, sphinx_tabs, sphinx_copybutton,
# sphinxext.opengraph, sphinxcontrib.jquery and notfound.extension.
# Only Ubuntu Pro Client-specific extensions are listed explicitly here.

extensions = [
    "canonical_sphinx",
    "sphinxcontrib.mermaid",
    "sphinx.ext.autosectionlabel",
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
html_context = {
    "product_page": "ubuntu.com/pro",
    "product_tag": "_static/circle_of_friends.png",
    # Documentation GitHub repository; used for the edit-page and
    # "Give feedback" links added by canonical_sphinx.
    "github_url": "https://github.com/canonical/ubuntu-pro-client",
    "repo_default_branch": "docs",
    "repo_folder": "/docs/",
    "github_issues": "enabled",
}

# Enable the top-of-page "Edit this page" button.
html_theme_options = {
    "source_edit_link": "https://github.com/canonical/ubuntu-pro-client",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# The Canonical theme's own static files (custom.css, furo_colors.css,
# header.css, github_issue_links.css/js, header-nav.js, favicon, ...) are
# provided by canonical_sphinx and must not be duplicated here. Only the
# Ubuntu Pro Client-specific assets are listed below.
html_static_path = ["_static"]

html_css_files = [
    "css/logo.css",
    "css/mermaid.css",
    "css/header.css",
    "css/highlight.css",
    "css/cookie-banner.css",
]
html_js_files = [
    "js/synced_tab_links.js",
    "js/bundle.js",
]
html_favicon = "_static/favicon.ico"


linkcheck_ignore = [
    "https://manpages.ubuntu.com/landscape-config",
    "https://manpages.ubuntu.com/apt.conf"
]


ogp_site_url = 'https://documentation.ubuntu.com/pro-client/en/latest/'
ogp_site_name = project
ogp_image = 'https://assets.ubuntu.com/v1/253da317-image-document-ubuntudocs.svg'

# The notfound_urls_prefix is computed automatically by canonical_sphinx
# from the project slug and the Read the Docs environment, so it is not set
# here. Only the custom 404 page content is kept.
notfound_context = {
    'title': 'Page not found',
    'body': '<h1>Page not found</h1>\n\n<p>Sorry, but the documentation page that you are looking for was not found.</p>\n<p>Documentation changes over time, and pages are moved around. We try to redirect you to the updated content where possible, but unfortunately, that didn\'t work this time (maybe because the content you were looking for does not exist in this version of the documentation).</p>\n<p>You can try to use the navigation to locate the content you\'re looking for, or search for a similar page.</p>\n',
}

copybutton_exclude = '.linenos, .gp'
