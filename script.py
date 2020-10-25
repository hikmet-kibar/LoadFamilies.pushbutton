import os
from pyrevit import forms, script

# Custom modules in lib/
from file_utils import FileFinder
from family_utils import FamilyLoader

logger = script.get_logger()
output = script.get_output()

"""
TODO:
    - Add docstrings
    - Add progress bar with CANCEL
      https://pyrevit.readthedocs.io/en/latest/pyrevit/forms.html#pyrevit.forms.ProgressBar
    - Add alerts instead of writing into output
      https://pyrevit.readthedocs.io/en/latest/pyrevit/forms.html#pyrevit.forms.alert
    - Maybe document check
      https://pyrevit.readthedocs.io/en/latest/pyrevit/forms.html#pyrevit.forms.alert

"""

# Get directory with families
directory = forms.pick_folder("Select parent folder of families")
logger.debug('Selected parent folder: {}'.format(directory))
if directory is None:
    logger.debug('No directory selected. Calling script.exit')
    script.exit()

# Find family files in directory
finder = FileFinder(directory)
logger.debug("Parent directory: {}".format(finder.directory))
finder.search('*.rfa')

# Excluding backup files
backup_pattern = r'^.*\.\d{4}\.rfa$'
finder.exclude_by_pattern(backup_pattern)
paths = finder.paths

# Dictionary to look up absolute paths by relative paths
path_dict = dict()
for path in paths:
    path_dict.update({os.path.relpath(path, directory): path})

# User input -> Select families from directory
family_select_options = sorted(
    path_dict.keys(),
    key=lambda x: (x.count(os.sep), x))  # Sort by nesting
selected_families = forms.SelectFromList.show(
    family_select_options,
    title="Select Families",
    width=500,
    button_name="Load Families",
    multiselect=True)
if selected_families is None:
    logger.debug('No families selected. Calling script.exit()')
    script.exit()
logger.debug('Selected Families: {}'.format(selected_families))

# Dictionary to look up FamilyLoader method by selected option
family_loading_options = {
    "Load all types": "load_all",
    "Load types by selecting individually": "load_selective"}
selected_loading_option = forms.CommandSwitchWindow.show(
    family_loading_options.keys(),
    message='Select loading option:',)
if selected_loading_option is None:
    logger.debug('No loading option selected. Calling script.exit()')
    script.exit()

# User input -> Select loading option (load all, load certain symbols)
logger.debug('Selected loading option: {}'.format(selected_loading_option))
laoding_option = family_loading_options[selected_loading_option]

# Loading selected families
already_loaded = set()
for family_path in selected_families:
    family = FamilyLoader(path_dict[family_path])
    logger.debug('Loading family: {}'.format(family.name))
    loaded = family.is_loaded
    if loaded:
        logger.debug('Family is already loaded: {}'.format(family.path))
        already_loaded.add(family)
    else:
        getattr(family, laoding_option)()

# Feedback on already loaded families
if len(already_loaded) != 0:
    output.print_md('### Families that were already loaded:')
    for family in sorted(already_loaded):
        print(family.path)
