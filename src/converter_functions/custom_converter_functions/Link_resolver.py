from src.converter_functions.converter_function import ConverterFunction
import pandas as pd 


class Link_resolver(ConverterFunction):
    '''
        Resolves linked config-json-parameters to the correspoinding target values
        Should always be executed before all other converter functions
    '''
    def __init__(self):
        super().__init__()

    def convert(self, variable_dict):
        to_return=dict()
        #checks if there's an intersection of key and value sets (indicates linked parameters)
        #and applies link resolution use parameter values of link targets
        #only str-type values are considered
        # ToDo_Thomas: I don't get the second sentence. Maybe use a short example to explain it (In theory I undersood it, but anyways)
        for key in variable_dict.keys():
            value=variable_dict[key]
            if type(value) is str and value in variable_dict.keys():
                to_return[key]=variable_dict[value]

        return to_return



