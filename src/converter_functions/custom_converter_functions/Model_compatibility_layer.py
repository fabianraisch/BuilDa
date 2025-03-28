from src.converter_functions.converter_function import ConverterFunction
import pandas as pd 


class Model_compatibility_layer(ConverterFunction):
    '''
        Ensures that model parameter values can be applied without conflict 
        by modifying user input parameter values of the configuration file accordingly. 
        E.g., avoid division by zero errors in model FMU by setting user input parameters 
        to be slightly greater than zero
    '''
    def __init__(self):
        super().__init__()
        
    @staticmethod
    def ensure_GT_zero(n):
        """
        Returns a value that is nearly zero if the input is zero; otherwise, returns the input value.

        Parameters:
        n (float): The input number to check.

        Returns:
        float: A small number if the input is zero, otherwise the input number.
        """
        replacement_value = 1e-5 
        return replacement_value if n == 0 else n
    
    def convert(self, variable_dict):
        list_gt_0=["fAInt","_distribution"]
        for key in variable_dict.keys():
            if any([sstr for sstr in list_gt_0 if sstr in key]):
                e=variable_dict[key]
                if isinstance(e,(float,int)):
                    variable_dict[key]=self.ensure_GT_zero(e)
                elif isinstance(e,(list,tuple)):
                    variable_dict[key]=[self.ensure_GT_zero(ee) for ee in e]
                elif isinstance(e,str):
                    #strings are explicitly ignored as they are handled by other converter functions or resolved to other input parameters
                    continue
                else: raise TypeError("No behaviour defined for type "+str(type(e))+" but parameter "+key+" in list of parameters that should be greater than zero.")
        tr=variable_dict
        return tr
