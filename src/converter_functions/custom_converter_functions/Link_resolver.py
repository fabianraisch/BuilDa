from src.converter_functions.converter_function import ConverterFunction
import pandas as pd 


class Link_resolver(ConverterFunction):
    '''
        Resolves linked config-json-parameters to the corresponding target values
        Should always be executed before all other converter functions
    '''
    def __init__(self):
        super().__init__()

    def convert(self, variable_dict):
        to_return=dict()
        #Checks if there's an intersection of key and value sets (indicates linked parameters).
        #If so, applies link resolution applying the values of the link targets parameters to the 
        #parameters where the link was configured.
        #e.g.: parameter1="parameter1"; parameter2=2 ---> parameter1=2
        #only str-type values are considered
        for key in variable_dict.keys():
            value=variable_dict[key]
            if type(value) is str and value in variable_dict.keys():
                to_return[key]=variable_dict[value]

        return to_return



