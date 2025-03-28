import os
import re
import random
from typing import List
from src.utils.util_functions import load_json

class Config:
    def __init__(self, 
                 config_path: os.path, 
                 fmu_path: os.path, 
                 output_path: os.path
                 ):
        
        ''' 
        Initialize the Configurator containing the config and other necessary information about the program.

        Args:
            - config_path: The path to the config json file.
            - fmu_path: The path to the fmu.
            - output_path: The path where the output of the simulations will be written to.

        Returns: None
        '''

        self.START_TIME_DEFAULT = 0.0
        self.STOP_TIME_DEFAULT = 86400
        self.WRITER_STEP_SIZE_DEFAULT = 900
        self.CONTROLLER_STEP_SIZE_DEFAULT = 900

        self.config_path = config_path
        self.fmu_path = fmu_path
        self.output_path = output_path

        self.fmu_name = os.path.split(self.fmu_path)[-1]
        
        # Parse the Config into a python dictionary object.        
        self.config = self.parse_config(load_json(self.config_path))
        
    def get(self, key):
        '''
        Retrieve a specific configuration parameter by key.

        Args:
            key: The key of the configuration parameter to retrieve.

        Returns:
            The value associated with the specified key.

        Raises:
            KeyError: If the key does not exist in the configuration.
        '''
        if key in self.config:
            return self.config[key]
        else:
            raise KeyError(f"Given key '{key}' does not exist in the configuration.")
        

    def parse_config(self, config):

        """ 
        Function to parse a variation configuration dictionary.

        Arguments:
            config: the variation configuration to parse.

        Returns:
            the parsed variation configuration.
        """
        
        # The default parsed configuration.
        parsed = {
            "variations": {

            },
            "variation_type": "default",
            "controller_name": None,
            "controller_step_size": self.CONTROLLER_STEP_SIZE_DEFAULT,
            "converter_functions": [],
            "start_time": self.START_TIME_DEFAULT,
            "stop_time": self.STOP_TIME_DEFAULT,        # Equals one day default
            "writer_step_size": self.WRITER_STEP_SIZE_DEFAULT,        # Equals 15 minutes default
            "columns_included": []                      # Default: include all columns
        }

        # Parse variations
        variations = config.get("variations", [])

        # Iterate over each specification to parse each values to a list.
        for variation in variations:
            list_for_perm = []
            if isinstance(variations[variation], list):     # List is already given
                list_for_perm = variations[variation]
            elif isinstance(variations[variation], str):      # List declaration via String
                list_for_perm = self.__parse_variation_string(variations[variation])
            elif isinstance(variations[variation],(float,int)):
                list_for_perm=[variations[variation]]
            else:
                raise ValueError("malformatted parameter set for '"+variation+"': "+str(variations[variation])+"  --> should be list, number or special string")

            parsed["variations"][variation] = list_for_perm

        # Parse validation_type
        variation_mode = config.get("variation_type", "default")
        parsed["variation_type"] = variation_mode

        # Parse the controller name
        parsed["controller_name"] =config.get("controller_name", None)

        # Parse the time settings if set in the config
        start_time = config.get("start_time", self.START_TIME_DEFAULT)
        if isinstance(start_time, (int, float)):
            parsed["start_time"] = int(start_time)
        stop_time = config.get("stop_time", self.STOP_TIME_DEFAULT)
        if isinstance(stop_time, (int, float)):
            parsed["stop_time"] = int(stop_time)
        step_size = config.get("writer_step_size", self.WRITER_STEP_SIZE_DEFAULT)
        if isinstance(step_size, (int, float)):
            parsed["writer_step_size"] = int(step_size)

        # Parse Controller step size (needed here because default step size could be used)
        controller_step_size = config.get("controller_step_size", self.CONTROLLER_STEP_SIZE_DEFAULT)
        if isinstance(controller_step_size, (int, float)):
            parsed["controller_step_size"] = int(controller_step_size)
        else:
            parsed["controller_step_size"] = parsed["writer_step_size"] # If no controller step size is given, the normal step size is used.

        # Parse converter functions
        converter_functions = config.get("converter_functions", None)
        if converter_functions:
            if isinstance(converter_functions, str): converter_functions = [converter_functions]
            parsed["converter_functions"] = converter_functions

        # Parse columns_included from the config file
        columns_included = config.get("columns_included", [])
        if isinstance(columns_included, list):
            parsed["columns_included"] = columns_included

        return parsed
    


    def __parse_variation_string(string):

        """ 
        Function to parse a variation string.

        Arguments:
            string: the variation string to parse.

        Returns:
            the variation values.

        Currently, there are the following patterns to parse:

        - [a, b, c, d]  -> [a, b, c, d]
        - "r (a, b, r)" -> [a, a+r, a+2r, ..., b] (range function)
        - "s (a, b, step, size) -> takes a sample from the discrete range [a, b] with step size step
        - "c (a, b, decimal_places, size) -> takes a sample from the continuous space [a, b] and rounds it.
        """

        nums = list(map(lambda x: int(x), re.findall(r'\d+', string)))

        if string[0] == "r":
            if len(nums) != 3:
                return []

            return [x for x in range(int(nums[0]), int(nums[1]) + 1, int(nums[2]))]

        elif string[0] == "s":
            if len(nums) != 4:
                return []

            if len(list(range(nums[0], nums[1] + 1, nums[2]))) >= nums[3]:  # Size greater than amount of samples.
                return list(range(nums[0], nums[1] + 1, nums[2]))

            return random.sample(range(nums[0], nums[1] + 1, nums[2]), nums[3])

        elif string[0] == "c":
            if len(nums) != 4:
                return []

            return [round(random.uniform(nums[0], nums[1]), nums[2]) for _ in range(nums[3])]

        else:
            return []
    

        
        



