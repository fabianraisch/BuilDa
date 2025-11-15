from src.utils.util_functions import get_converter_function_by_string

class Converter():

    def __init__(self, deault_dict, converter_function_names = [], exclude_function_names = []):
        '''
        Init the Converter. Takes a list of converter function names to retrieve the converter function for later use.

        Args:
        - converter_function_names [list[str]]: A list of identifying converter function names.
        - exclude_function_names [list[str]]: Subset of converter_function_names that is to be ignored

        Returns: None.
        '''

        self.converter_function_names = converter_function_names

        self.converter_functions = []

        for converter_function_name in converter_function_names:
            if not converter_function_name in exclude_function_names:

                converter_function = get_converter_function_by_string(converter_function_name)

                if not converter_function:
                    print(f"Could not find converter function with name {converter_function_name} -> Skipping ...")
                    continue

                self.converter_functions.append(converter_function)

        self.fmu_default_dict = deault_dict 

        self.conversion_result_last_dict=self.fmu_default_dict

    def convert(self, variations):
        '''
        Function to convert the variations (in-place).

        Args: 
            - variations: A list of all variations. It looks like this: [(Param1, new_value), (Param2, new_value), ...]
        
        '''
        variation_dict = {}

        for variation in variations: 
            variation_dict[variation[0]] = variation[1]

        conversion_result_dict = {}

        for converter_function in self.converter_functions:


            convert_dict = {}

            #%%include all variables defined as fmu parameters and config parameters in the converter function variables
            #default: fmu-parameter values --> superseded by config-parameter values (possibly) --> superseded by Converter-Function output (possibly)
            convert_dict.update(self.fmu_default_dict)
            convert_dict.update(variation_dict)
            convert_dict.update(conversion_result_dict)

            conversion_result_dict.update(converter_function.convert(convert_dict))

        variation_dict.update(conversion_result_dict)
        
        #%%filter: keep only...
        #...parameters that exist as fmu parameters
        ##debug print: difference-set of converter function output and fmu parameters to check, if there are naming errors:
        #print(variation_dict.keys() ^ self.fmu_default_dict.keys())
        fmu_parameters_to_update_lists=[(k,v) for k,v in variation_dict.items() if k in self.fmu_default_dict.keys() and v!=self.conversion_result_last_dict[k]]
                                                                                                                        #^^^ why?
        self.conversion_result_last_dict=conversion_result_dict
        return fmu_parameters_to_update_lists

