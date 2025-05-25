#!/usr/bin/env python3
from src.utils.config import Config
from src.fmuwrapper import FMUWrapper
from src.converter import Converter
from src.variator import Variator
from src.controllers.controller_wrapper import ControllerWrapper
from src.utils.util_functions import get_step_size_arr

class SimulationController:
    '''
    This class handles the simulation of the model in the FMU. It provides an interface to the external controllers 
    and manages the generated simulation output to be written after the simulation.
    '''
    def __init__(self, worker_id: int, config: Config, variation: Variator):
        self.id = worker_id
        self.config = config
        self.variation = variation

        self.fmu_wrapper = FMUWrapper(fmu_path=config.fmu_path, 
                                       start_time=config.get("start_time"))
        

        self.step_size_arr = get_step_size_arr(config.get("start_time"),
                                                config.get("stop_time"),
                                                config.get("writer_step_size"),
                                                config.get("controller_step_size"),
                                                max_permitted_time_step=config.get_max_permitted_time_step())

        
        self.out_cols = ["timestamp"] + \
            list(set(self.fmu_wrapper.vrs.keys()).intersection(config.get("columns_included")))
        
        #%%initialization of FMU
        self.fmu_wrapper.fmu.enterInitializationMode()        
        self.converter = Converter(self.fmu_wrapper.fmu_default_dict, 
                            config.get("converter_functions"))
        self.converted_variation = self.converter.convert(variation)
        self.fmu_wrapper.alter_in_fmu(param_dict=dict(self.converted_variation))
        self.fmu_wrapper.fmu.exitInitializationMode()
        self.fmu_wrapper.test_fmu_parameterizing(parameters=dict(self.converted_variation),
                                                 b_verbose_mode=False)
        
        self.controller_wrapper = ControllerWrapper(config.get("controller_name"),
                                            config.get("controller_step_size"),
                                            self.fmu_wrapper)

        self.controller_wrapper.configure_controllers()


    def generate_output_check(self, curr_time_relative):
        '''
        Determines if output should be generated at the current simulation time.
        Returns a boolean indicating whether output should be generated based on the elapsed simulation time and the `controller_step_size` parameter from the configuration.

        Parameters:
            curr_time_relative (float): The simulation time, elapsed since simulation start time

        Returns:
            bool: True if output should be generated, False otherwise.
        '''
        if curr_time_relative % self.config.get("writer_step_size") == 0:
            return True 
        else:
            return False

    def generate_output(self, curr_time, fmu_state_dict):
        '''
        Generates and returns a new result row for the current simulation time.

        This method creates a list containing the current time as an integer and appends values from the `fmu_state_dict` for each output column, skipping the timestamp header.

        Parameters:
            curr_time (float): The current simulation time.
            fmu_state_dict (dict): A dictionary containing the current state of the FMU variables.

        Returns:
            list: A list representing the result row for the current simulation time.
        '''    
        row = [int(curr_time)]
        for key in self.out_cols[1:]: # skip the timestamp header
            row.append(fmu_state_dict[key])
        return row

    def simulate_fmu(self):
        '''
        Executes one simulation of the model step by step, handling all model inputs and outputs during the simulation and returning the results.

        Returns:
            - rows (list): The generated output rows from the simulation.
            - out_cols (list): The output column headers.
            - converted_variation: The converted variation data.

        Parameters:
            None
        '''
        rows = []

        self.fmu_wrapper.save_current_fmu_variables("fmu_initial_state.csv")

        for step_size in self.step_size_arr:
            
            #calculate simulation time since simulation start time
            curr_time_relative=self.fmu_wrapper.time-self.config.get("start_time")
            b_perform_control = self.controller_wrapper.perform_control_check(curr_time_relative=
                                                                            curr_time_relative)
            
            b_generate_output = self.generate_output_check(curr_time_relative=curr_time_relative)

            variables_to_read = []
            if b_perform_control:
                variables_to_read += self.controller_wrapper.get_variables_to_read()

            if b_generate_output:
                variables_to_read += self.out_cols[1:]

            fmu_state_dict = self.fmu_wrapper.get_fmu_state_dict(variables_to_read=variables_to_read)

            if b_perform_control:
                self.controller_wrapper.handle_control_action(curr_time=self.fmu_wrapper.time, 
                                                              fmu_state_dict=fmu_state_dict)

            #read out again variables from fmu to get recent values influenced by controller (e.g. totalHeatingPower.y influenced by controller output ctrSignalHeating) (no doStep is necessary here) 
            fmu_state_dict = self.fmu_wrapper.get_fmu_state_dict(variables_to_read=variables_to_read)

            if b_generate_output:
                rows.append(self.generate_output(curr_time=self.fmu_wrapper.time, 
                                              fmu_state_dict=fmu_state_dict))

            self.fmu_wrapper.step_FMU(step_size=step_size)
            
        return rows, self.out_cols, self.converted_variation