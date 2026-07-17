import datetime
import os
import textwrap

# Configuration for the Sphinx documentation builder.
# All configuration specific to your project should be done in this file.
#
# This project uses the extension-based Sphinx Stack. Behaviour that is common
# to all Canonical documentation is provided by the 'canonical_sphinx' extension
# and its dependencies; only Ubuntu Pro Client-specific configuration lives here.
#
# A complete list of built-in Sphinx configuration values:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
#
# The Sphinx Stack uses the Canonical Sphinx theme to keep all documentation
# consistent and on brand:
# https://github.com/canonical/canonical-sphinx

#######################
# Project information #
#######################

# Project name
project = "Ubuntu Pro Client"

# Author name; used in the default copyright statement in the page footer
author = "Canonical Group Ltd"

# The year in the copyright statement
copyright = "%s, %s" % (datetime.date.today().year, author)

# Sidebar documentation title
# To disable the title, set it to an empty string.
html_title = project + " documentation"

# Documentation website URL
#
# Set the URL where the documentation will be hosted so that it is used for the
# Open Graph link preview and the sitemap. On Read the Docs the canonical URL is
# provided automatically.
ogp_site_url = os.environ.get(
    "READTHEDOCS_CANONICAL_URL",
    "https://documentation.ubuntu.com/pro-client/en/latest/",
)

# Preview name of the documentation website
ogp_site_name = project

# Preview image URL
ogp_image = "https://assets.ubuntu.com/v1/253da317-image-document-ubuntudocs.svg"

# Dictionary of values to pass into the Sphinx context for all pages:
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-html_context
html_context = {
    # Product page URL; can be different from product docs URL
    "product_page": "https://ubuntu.com/pro",
    # Product tag image; the orange part of the logo, shown in the page header
    "product_tag": "_static/circle_of_friends.png",
    # Documentation GitHub repository URL
    "github_url": "https://github.com/canonical/ubuntu-pro-client",
    # Docs branch in the repo; used in links for viewing the source files
    "repo_default_branch": "docs",
    # Docs location in the repo; used in links for viewing the source files
    "repo_folder": "/docs/",
    # Enable or disable the Previous / Next buttons at the bottom of pages
    # Valid options: none, prev, next, both
    "sequential_nav": "none",
    # Required for the feedback button and the issue link in the footer
    "github_issues": "enabled",
    # Passes the top-level 'author' value to the theme
    "author": author,
    # Header links used by the custom Ubuntu Pro header template
    "pro_overview": "https://documentation.ubuntu.com/pro",
    "client_docs": "https://documentation.ubuntu.com/pro-client/en/latest/",
    "pro_service_esm": "https://ubuntu.com/security/esm",
    "pro_service_livepatch": "https://ubuntu.com/security/livepatch",
    "pro_service_fips": "https://ubuntu.com/security/fips",
    "pro_service_usg": "https://ubuntu.com/security/certifications/docs/usg",
    "pro_service_cc": "https://ubuntu.com/security/cc",
    "pro_service_anbox": "https://anbox-cloud.io/",
    "pro_service_ros": "https://ubuntu.com/robotics/ros-esm",
    "pro_service_realtime": "https://ubuntu.com/realtime-kernel",
}

# Enable the edit button on pages, pointing at the documentation GitHub repo.
html_theme_options = {
    "source_edit_link": "https://github.com/canonical/ubuntu-pro-client",
}

# Project slug
# This documentation is hosted on https://documentation.ubuntu.com/pro-client/.
slug = "pro-client"

#######################
# Sitemap configuration: https://sphinx-sitemap.readthedocs.io/
#######################

# Use RTD canonical URL to ensure duplicate pages have a specific canonical URL
html_baseurl = os.environ.get(
    "READTHEDOCS_CANONICAL_URL",
    "https://documentation.ubuntu.com/pro-client/en/latest/",
)

# sphinx-sitemap uses html_baseurl to generate the full URL for each page:
sitemap_url_scheme = "{link}"

# Include `lastmod` dates in the sitemap:
sitemap_show_lastmod = True

# Pages excluded from the sitemap:
sitemap_excludes = [
    "404/",
    "genindex/",
    "search/",
]

################################
# Template and asset locations #
################################

# The custom Ubuntu Pro header (Pro services dropdown) and footer templates.
templates_path = ["_templates"]

# Custom static assets (Pro tag image, Pro header CSS/JS and code-block styling).
html_static_path = ["_dev/_static"]

# Google Search Console site-verification file, served verbatim at the docs root.
html_extra_path = ["googleaf254801a5285c31.html"]

#############
# Redirects #
#############

# Internal (rediraffe) redirects. Add mappings to the 'redirects.txt' file.
# https://sphinxext-rediraffe.readthedocs.io/en/latest/
rediraffe_redirects = "redirects.txt"
rediraffe_branch = "docs"

# Strips '/index.html' from destination URLs when building with 'dirhtml'
rediraffe_dir_only = True

############################
# sphinx-llm configuration #
############################

# This description is included in llms.txt to provide some initial context for
# the product docs.
llms_txt_description = textwrap.dedent(
    """\
    Documentation for Ubuntu Pro Client (the pro command), used to enable and
    manage Ubuntu Pro services such as ESM, Livepatch and FIPS.
    """
)

# The base URL for references built by sphinx-markdown-builder.
if os.environ.get("READTHEDOCS"):
    markdown_http_base = html_baseurl

###########################
# Link checker exceptions #
###########################

# A regex list of URLs that are ignored by 'make linkcheck'
linkcheck_ignore = [
    "https://manpages.ubuntu.com/landscape-config",
    "https://manpages.ubuntu.com/apt.conf",
    # Requires authentication, so linkcheck always sees an "unauthorized" page.
    "https://support-portal.canonical.com/*",
]

# A regex list of URLs where anchors are ignored by 'make linkcheck'.
# wiki.debian.org serves an anti-bot challenge page to linkcheck, so the real
# anchors can't be detected and are reported as missing.
linkcheck_anchors_ignore_for_url = [r"https://wiki\.debian\.org/.*"]

# Give linkcheck multiple tries on failure (e.g. transient manpages timeouts).
linkcheck_retries = 3

########################
# Configuration extras #
########################

# Custom Sphinx extensions; see
# https://www.sphinx-doc.org/en/master/usage/extensions/index.html
# NOTE: 'canonical_sphinx' provides the theme and the common Canonical
# configuration. 'sphinxcontrib.mermaid' is added on top of the default stack
# because Ubuntu Pro Client docs use Mermaid diagrams (e.g. cves_and_usns).
# 'sphinx.ext.autosectionlabel' generates the section labels the docs
# cross-reference by title.
extensions = [
    "canonical_sphinx",
    "notfound.extension",
    "sphinx_design",
    "sphinx_rerediraffe",
    "sphinx_reredirects",
    "sphinx_tabs.tabs",
    "sphinxcontrib.jquery",
    "sphinxext.opengraph",
    "sphinx_config_options",
    "sphinx_contributor_listing",
    "sphinx_filtered_toctree",
    "sphinx_llm.txt",
    "sphinx_related_links",
    "sphinx_roles",
    "sphinx_terminal",
    "sphinx_ubuntu_images",
    "sphinx_youtube_links",
    "sphinxcontrib.cairosvgconverter",
    "sphinx_last_updated_by_git",
    "sphinx.ext.intersphinx",
    "sphinx_sitemap",
    "sphinxcontrib.mermaid",
    "sphinx.ext.autosectionlabel",
]

# Generate unique section labels prefixed by the document path.
autosectionlabel_prefix_document = True

# Request automatic anchors for headings down to the given depth.
myst_heading_anchors = 3

# Excludes files or directories from processing
exclude_patterns = [
    "doc-cheat-sheet*",
    ".venv*",
]

# Adds custom CSS files, located in 'html_static_path' or remotely.
# The remote cookie-banner stylesheet restores the Ubuntu cookie policy styling;
# 'pro-header.css' styles the Ubuntu Pro "Pro services" header dropdown;
# 'mermaid.css' and 'highlight.css' add Pro Client-specific rendering tweaks.
html_css_files = [
    "https://assets.ubuntu.com/v1/d86746ef-cookie_banner.css",
    "pro-header.css",
    "mermaid.css",
    "highlight.css",
]

# Adds custom JavaScript files, located in 'html_static_path' or remotely.
# The remote bundle.js provides the cookie policy banner and analytics;
# 'pro-header-nav.js' toggles the Ubuntu Pro "Pro services" header dropdown.
html_js_files = [
    "https://assets.ubuntu.com/v1/287a5e8f-bundle.js",
    "pro-header-nav.js",
]

# Custom content for the 404 (page not found) page.
notfound_context = {
    "title": "Page not found",
    "body": (
        "<h1>Page not found</h1>\n\n"
        "<p>Sorry, but the documentation page that you are looking for was not "
        "found.</p>\n"
        "<p>Documentation changes over time, and pages are moved around. We try "
        "to redirect you to the updated content where possible, but "
        "unfortunately, that didn't work this time (maybe because the content "
        "you were looking for does not exist in this version of the "
        "documentation).</p>\n"
        "<p>You can try to use the navigation to locate the content you're "
        "looking for, or search for a similar page.</p>\n"
    ),
}
