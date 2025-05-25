from abc import ABC
import pandas as pd

class ConverterFunction(ABC):

    def __init__(self):

        '''
        Init function of the Converter Function abstract base class.

        '''
        pass
    

    def convert(self, variable_dict):
        '''
        The function to convert a dict of fmu parameter / variations into a new set of variations.

        This function must be implemented in every class that extends this ABC.
        '''

        return NotImplementedError("Function convert not implemented in this ConverterFunction. Please override this method first.")
