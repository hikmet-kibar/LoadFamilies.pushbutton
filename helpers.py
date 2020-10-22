import pathlib
import re

from pyrevit.framework import clr
from pyrevit import forms, revit, DB, script

logger = script.get_logger()


class FamilyLoader:
    """
    Enables loading a family from an absolute path.

    Example:
    family = FamilyLoader("absolute/path/to/my/family")
    if not family.is_loaded:
        family.load_selective() # OR family.load_all()
    """
    def __init__(self, path):
        self.path = path
        self.name = pathlib.PurePath(path).name.replace(".rfa", "")

    @property
    def is_loaded(self):
        """ Checks if family name already exists in project """
        collector = DB.FilteredElementCollector(revit.doc).OfClass(DB.Family)
        condition = (x for x in collector if x.Name == self.name)
        return next(condition, None) is not None

    def get_symbols(self):
        """
        Loads family in a fake transaction to return all symbols.

        Remark:
        Uses SmartSortableFamilySymbol for effective sorting
        """
        logger.debug('Fake loading family: {}'.format(self.name))
        symbol_set = set()
        with revit.ErrorSwallower():
            # DryTransaction will rollback all the changes
            with revit.DryTransaction('Fake load'):
                ret_ref = clr.Reference[DB.Family]()
                revit.doc.LoadFamily(self.path, ret_ref)
                loaded_fam = ret_ref.Value
                # Get the symbols
                for symbol_id in loaded_fam.GetFamilySymbolIds():
                    symbol = revit.doc.GetElement(symbol_id)
                    symbol_name = revit.query.get_name(symbol)
                    sortable_sym = SmartSortableFamilySymbol(symbol_name)
                    logger.debug('Importable Symbol: {}'.format(sortable_sym))
                    symbol_set.add(sortable_sym)
        return sorted(symbol_set)

    def load_selective(self):
        """
        Loads the family and only selected symbols.

        Based on Ehsan Iran-Nejads 'Load More Types'
        """
        # User input -> Select family symbols
        options = self.get_symbols()  # Get a set with the symbols
        selected_symbols = forms.SelectFromList.show(
            options,
            title=self.name,
            button_name="Load type(s)",
            multiselect=True)
        if selected_symbols is None:
            logger.debug('No family symbols selected.')
            return
        logger.debug('Selected symbols are: {}'.format(selected_symbols))

        # Load family with selected symbols
        with revit.Transaction('Loaded {}'.format(self.name)):
            try:
                for symbol in selected_symbols:
                    logger.debug('Loading symbol: {}'.format(symbol))
                    revit.doc.LoadFamilySymbol(self.path, symbol.symbol_name)
                logger.debug('Successfully loaded all selected symbols')
            except Exception as load_err:
                logger.error(
                    'Error loading family symbol from {} | {}'
                    .format(self.path, load_err))
                raise load_err

    def load_all(self):
        """ Loads family and all its symbols. """
        with revit.Transaction('Loaded {}'.format(self.name)):
            try:
                revit.doc.LoadFamily(self.path)
                logger.debug(
                    'Successfully loaded family: {}'.format(self.name))
            except Exception as load_err:
                logger.error(
                    'Error loading family symbol from {} | {}'
                    .format(self.path, load_err))
                raise load_err


class SmartSortableFamilySymbol:
    """
    Enables smart sorting of family symbols.

    Example:
    symbol_set = set()
    for family_symbol in familiy_symbols:
        family_symbol_name = revit.query.get_name(family_symbol)
        sortable_sym = SmartSortableFamilySymbol(family_symbol_name)
        symbol_set.add(sortable_sym)
    sorted_symbols = sorted(symbol_set)

    Copied from Ehsan Iran-Nejads SmartSortableFamilyType
    in 'Load More Types'
    """
    def __init__(self, symbol_name):
        self.symbol_name = symbol_name
        self.sort_alphabetically = False
        self.number_list = [
            int(x)
            for x in re.findall(r'\d+', self.symbol_name)]
        if not self.number_list:
            self.sort_alphabetically = True

    def __str__(self):
        return self.symbol_name

    def __repr__(self):
        return '<SmartSortableFamilySymbol Name:{} Values:{} StringSort:{}>'\
               .format(self.symbol_name,
                       self.number_list,
                       self.sort_alphabetically)

    def __eq__(self, other):
        return self.symbol_name == other.symbol_name

    def __hash__(self):
        return hash(self.symbol_name)

    def __lt__(self, other):
        if self.sort_alphabetically or other.sort_alphabetically:
            return self.symbol_name < other.symbol_name
        else:
            return self.number_list < other.number_list
