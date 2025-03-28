from src.converter_functions.converter_function import ConverterFunction
import pandas as pd 


class NaiveConverterFunction(ConverterFunction):

    '''
    An exmple of a custom Conveter Function. You can use this as a blueprint.

    Every custom converter function must implement the ConverterFunction ABC. If not, the concept does not work.
    '''

    def __init__(self):
        '''
        Example init function of a custom converter function.
        '''

        super().__init__()

    def convert(self, variable_dict):
        '''
        Example of converting a dict of variables (for variations). 
        You can use this as a blueprint.
        '''

        to_return = {}

        to_return["A_room_start"] = variable_dict["A_room_start"] * 2

        return to_return


