#!/usr/bin/env python3
from src.utils.config import Config
from src.fmuwrapper import FMUWrapper
from src.converter import Converter
from src.variator import Variator
from src.controllers.controller_wrapper import ControllerWrapper
from src.utils.util_functions import get_step_size_arr
from src.utils.schedule_utils import parse_schedule, schedule_step_size_array, get_index_from_dict_like_array, check_for_invalid_keys
import copy

class SimulationController:
    '''
    This class handles the simulation of the model in the FMU. It provides an interface to the external controllers 
    and manages the generated simulation output to be written after the simulation.

    Parameters:
        worker_id: id of the variation and process
        config: Config object containing all non-variated parameters
        variation: dict-like list of tuples (<param_name>, <value>) containing all variated parameters
        schedule: if passed, contains retrofits and/or occupancy changes.
    '''
    def __init__(self, worker_id: int, config: Config, variation: list, schedule: dict = None):
        self.id = worker_id
        self.config = config
        self.variation = variation

        self.setup_FMU(self.config, self.variation, self.config.get("start_time"))

        
        
        if schedule:
            
            schedule = parse_schedule(schedule, config.get("start_time"), config.get("stop_time"))
            check_for_invalid_keys(schedule, config.config["variations"])

            # parse retrofits into array that correlates with halting points, accumulate retrofits
            self.variation_updates = [dict(variation)]
            for index, timestamp in enumerate(schedule):

                # if heatPower was updated last step but should not be updated this time, remove key
                remove_heater_update = False
                if "Heater" in self.variation_updates[-1] and not "Heater" in schedule[timestamp]:
                    remove_heater_update = True
                self.variation_updates[-1].update(schedule[timestamp])
                if remove_heater_update:
                    self.variation_updates[-1].pop("Heater")
                self.variation_updates.append(copy.deepcopy(self.variation_updates[index]))


            self.variation_updates = [list(i.items()) for i in self.variation_updates]

            # if schedule is provided, calculate halting points for retrofits
            self.step_size_arr, self.start_times = schedule_step_size_array(config.get("start_time"),
                                                    config.get("stop_time"),
                                                    config.get("writer_step_size"),
                                                    self.controller_wrapper.controller_step_size,
                                                    max_permitted_time_step=config.get_max_permitted_time_step(),
                                                    schedule = schedule)

        # else if no schedule is provided, compute time steps for simulation
        else:

            self.step_size_arr = [get_step_size_arr(config.get("start_time"),
                                                    config.get("stop_time"),
                                                    config.get("writer_step_size"),
                                                    self.controller_wrapper.controller_step_size,
                                                    max_permitted_time_step=config.get_max_permitted_time_step())]
            self.start_times = [config.get("start_time")]


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
        If self.step_size_arr contains multiple timeseries, updates the fmu with the retrofits specified in self.variation_updates.

        Returns:
            - rows (list): The generated output rows from the simulation.
            - out_cols (list): The output column headers.
            - converted_variation: The converted variation data.

        Parameters:
            None
        '''
        rows = []

        self.fmu_wrapper.save_current_fmu_variables("fmu_initial_state.csv")

        for index, schedule in enumerate(self.step_size_arr):

            #print(schedule)
            for step_size in schedule:
                
                #calculate simulation time since simulation start time
                curr_time_relative=self.fmu_wrapper.time-self.start_times[index]
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


            # if another timesieries follows in step_size_array, update parameters according to self.variation_updates
            if index < len(self.step_size_arr)-1:
                self.setup_FMU(self.config, self.variation_updates[index], self.start_times[index+1], re_initialization = True)
            


            
        return rows, self.out_cols, list(self.converted_variation.items())


    def setup_FMU(self, config, variation, start_time, re_initialization = False):
        '''
        Instantiates the FMU_Wrapper and Converter objects anew and sets up a fresh FMU Object.

        Arguments:
            - config: the config object passed down from the main. Contains all static parameters for simulation
            - variation: Parameters to update according to a variation (specified through config via arrays) or retrofit (generated in SimulationController.__init__())
            - re_initialization: Flag that tells setup_FMU() to keep old parameters that are not generated anew (e.g. heatingPower)


        '''

        # if FMU is re-initialized, keep nominal heating and cooling power (do not calculate anew from retrofitted parameters)
        if re_initialization:
            exclude_functions = ["Nominal_heating_power_calculator", "Nominal_cooling_power_calculator"]
        else:
            # else: First setup - instantiate new converted_variation dict and execute all converter funtions.
            exclude_functions = []
            self.converted_variation = {}

        # if a heater retrofit is desired, execute the heating and cooling power converter functions on the new parameters
        if get_index_from_dict_like_array(variation, "Heater") >= 0:
            exclude_functions = []



        self.fmu_wrapper = FMUWrapper(fmu_path=config.fmu_path, 
                                       start_time=start_time)

        
        self.out_cols = ["timestamp"] + \
            list(set(self.fmu_wrapper.vrs.keys()).intersection(config.get("columns_included")))
        
        #%%initialization of FMU
        self.fmu_wrapper.fmu.enterInitializationMode()        
        self.converter = Converter(self.fmu_wrapper.fmu_default_dict, 
                            config.get("converter_functions"),
                            exclude_function_names = exclude_functions)


        # update possibly existing converted_variations (that e.g. contain heatingPower) with newly computed values
        self.converted_variation.update(self.converter.convert(variation))

        self.fmu_wrapper.alter_in_fmu(param_dict=dict(self.converted_variation))

        self.fmu_wrapper.fmu.exitInitializationMode()
        self.fmu_wrapper.test_fmu_parameterizing(parameters=dict(self.converted_variation),
                                                 b_verbose_mode=False)
        
        self.controller_wrapper = ControllerWrapper(config.get("controller_name"),
                                            config.get("controller_step_size"),
                                            self.fmu_wrapper)

        self.controller_wrapper.configure_controllers()