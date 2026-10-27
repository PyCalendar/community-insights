"""Sphinx configuration for the community-insights documentation."""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # community_insights.errors for autodoc

project = "Contributor Community Insights"
copyright = f"{datetime.date.today().year}, community-insights contributors"  # noqa: A001
author = "community-insights contributors"

extensions = [
    "notfound.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_issues",
    "sphinx_last_updated_by_git",
    "sphinxcontrib.mermaid",
]

html_baseurl = "https://community-insights.readthedocs.io/en/latest/"
issues_github_path = "PyCalendar/community-insights"

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/PyCalendar/community-insights",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
    ],
    "logo": {"text": "Contributor Community Insights"},
    "show_toc_level": 2,
    "navigation_with_keys": True,
    "article_footer_items": ["last-updated"],
}
html_last_updated_fmt = "%Y-%m-%d"
html_context = {
    "github_user": "PyCalendar",
    "github_repo": "community-insights",
    "github_version": "main",
    "doc_path": "docs",
}
html_static_path = ["_static"]
html_css_files = ["style.css"]

mermaid_output_format = "raw"
mermaid_version = "12.1.0"
mermaid_init_config = {"startOnLoad": False, "fontFamily": "var(--pst-font-family-base)"}

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
exclude_patterns = ["_build"]

# make linkcheck
linkcheck_ignore = [
    r"http://localhost",  # the site started while developing
    # Files of this repository: a new one is on GitHub only after its pull request is merged.
    r"https://github\.com/PyCalendar/community-insights/(blob|tree)/",
]
linkcheck_allowed_redirects = {
    # Pages of GitHub that need a login, such as the settings.
    r"https://github\.com/.*": r"https://github\.com/login\?return_to=.*",
    r"https://docs\.djangoproject\.com/en/stable/.*": r"https://docs\.djangoproject\.com/en/\d.*",
    r"https://[\w-]+\.readthedocs\.io/": r"https://[\w-]+\.readthedocs\.io/en/latest/",
}
linkcheck_retries = 3
linkcheck_report_timeouts_as_broken = False
