from src.converter_functions.converter_function import ConverterFunction
import pandas as pd 


class Miscellaneous_handler(ConverterFunction):
    '''
        Handles everything that does require a separate converter function
    '''
    def __init__(self):
        super().__init__()

    def convert(self, variable_dict):
        to_return = variable_dict

        # Convert config.json parameter names to fmu-parameter names, where necessary
        to_return["UseInternalController.k"]=to_return["UseInternalController"]
        to_return["weaDat.filNam"]=to_return["weaDat.fileName"]

        # Assign value for U-value radiation correction
        to_return["corGDouPan.UWin"] = to_return["UWin"] 

        return to_return

