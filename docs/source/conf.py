"""Configuration file for the Sphinx documentation builder."""

from datetime import date
from os.path import abspath, dirname
from pathlib import Path
import tomllib

INSTITUTE_NAME = "Allen Institute for Neural Dynamics"

current_year = date.today().year
this_file_path = abspath(__file__)
project_root = Path(dirname(dirname(dirname(this_file_path))))

project = "harp-updater-gui"
project_copyright = f"{current_year}, {INSTITUTE_NAME}"
author = INSTITUTE_NAME

pyproject_path = project_root / "pyproject.toml"
pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
release = pyproject_data["project"]["version"]

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.napoleon",
    "sphinx_jinja",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = []

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
master_doc = "index"

myst_enable_extensions = [
    "colon_fence",
]
myst_heading_anchors = 3

html_theme = "furo"
html_static_path = ["_static"]
html_title = "Harp Updater GUI Docs"
html_favicon = "_static/app_icon_color.ico"
html_logo = "_static/app_icon_color.ico"
html_theme_options = {
    "source_repository": "https://github.com/AllenNeuralDynamics/harp-updater-gui/",
    "source_branch": "main",
    "source_directory": "docs/source/",
}


def setup(app):
    app.add_css_file("custom.css")


html_show_sphinx = False
html_show_copyright = False
