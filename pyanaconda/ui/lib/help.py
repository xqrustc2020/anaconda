#
# Copyright (C) 2014  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
"""
Anaconda built-in help module
"""
import os

from pyanaconda.core.configuration.anaconda import conf
from pyanaconda.localization import find_best_locale_match
from pyanaconda.core.constants import DEFAULT_LANG, HELP_MAIN_PAGE_GUI, HELP_MAIN_PAGE_TUI
from pyanaconda.core.util import startProgram

from pyanaconda.anaconda_loggers import get_module_logger
log = get_module_logger(__name__)

yelp_process = None


def _get_best_help_file(help_file):
    """
    Return the path to the best help file for the current language and available
    help content

    :param str help_file: name of the requested help file
    :return: path to the best help file or ``None`` is no match is found
    :rtype: str or NoneType

    """
    help_folder = conf.ui.help_directory
    current_lang = os.environ["LANG"]
    # list all available languages for the Anaconda help
    # * content is stored in folders named after the given language code
    #   (en-US, cs-CZ, jp-JP, etc.)
    # * we check if the given folder contains the currently needed help file
    #   and only consider it fit to use if it does have the file
    if not os.path.exists(help_folder):
        log.warning("help folder %s for help file %s does not exist", help_folder, help_file)
        return None

    # Collect languages and files that provide the help content.
    help_langs = {}

    for lang in os.listdir(help_folder):
        # Does the help file exist for this language?
        path = os.path.join(help_folder, lang, help_file)
        if not os.path.isfile(path):
            continue

        # Create a valid langcode. For example, use en_US instead of en-US.
        code = lang.replace('-', '_')
        help_langs[code] = path

    # Find the best help file.
    for locale in (current_lang, DEFAULT_LANG):
        best_lang = find_best_locale_match(locale, help_langs.keys())
        best_path = help_langs.get(best_lang, None)

        if best_path:
            return best_path

    # No file found.
    log.warning("no help content found for file %s", help_file)
    return None


def get_help_path(help_file, plain_text=False):
    """
    Return the full path for the given help file name,
    if the help file path does not exist a fallback path is returned.
    There are actually two possible fallback paths that might be returned:

    * first we try to return path to the main page of the installation guide
      (if it exists)
    * if we can't find the main page of the installation page, path to a
      "no help found" placeholder bundled with Anaconda is returned

    Regarding help l10n, we try to respect the current locale as defined by the
    "LANG" environmental variable, but fallback to English if localized content
    is not available.

    :param help_file: help file name
    :type help_file: str or NoneType

    :param plain_text: should we find the help in plain text?
    :type plain_text: bool

    :return str: full path to the help file requested or to a placeholder
    """
    # help l10n handling

    if help_file:
        help_path = _get_best_help_file(help_file)
        if help_path is not None:
            return help_path

    # setup the fallback files
    if plain_text:
        main_page = HELP_MAIN_PAGE_TUI
        placeholder = conf.ui.default_help_pages[0]
    elif not conf.system.provides_web_browser:
        main_page = HELP_MAIN_PAGE_GUI
        placeholder = conf.ui.default_help_pages[1]
    else:
        main_page = HELP_MAIN_PAGE_GUI
        placeholder = conf.ui.default_help_pages[2]

    # the screen did not have a helpFile defined or the defined help file
    # does not exist, so next try to check if we can find the main page
    # of the installation guide and use it instead
    help_path = _get_best_help_file(main_page)
    if help_path is not None:
        return help_path

    # looks like the installation guide is not available, so just return
    # a placeholder page, which should be always present
    return _get_best_help_file(placeholder)


def start_yelp(help_path):
    """
    Start a new yelp process and make sure to kill any existing ones

    :param help_path: path to the help file yelp should load
    :type help_path: str or NoneType
    """

    kill_yelp()
    log.debug("starting yelp")
    global yelp_process
    # under some extreme circumstances (placeholders missing)
    # the help path can be None and we need to prevent Popen
    # receiving None as an argument instead of a string
    yelp_process = startProgram(["yelp", help_path or ""], reset_lang=False)


def kill_yelp():
    """Try to kill any existing yelp processes"""

    global yelp_process
    if not yelp_process:
        return False

    log.debug("killing yelp")
    yelp_process.kill()
    yelp_process.wait()
    yelp_process = None
    return True
