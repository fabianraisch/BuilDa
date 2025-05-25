from typing import List
from src.fmuwrapper import FMUWrapper
from src.utils.util_functions import get_controller_by_string

class ControllerWrapper:
    '''
    This class provides functions to handle:

    - Controller configuration
    - Decision-making regarding whether a control action should be performed at the current time step
    - Information gathering about the variables needed from the FMU for the control actions
    - The control actions themselves

    The controller wrapper object acts as an interface between the controller classes and the simulation loop.
    '''
    def __init__(self, 
                 controller_names: List[str],
                 controller_step_size: int,
                 fmu_wrapper: FMUWrapper):


        #%%instantiation of controllers
        self.controllers=list()
        b_internal_heating_controller_active=bool(list(fmu_wrapper.get_fmu_state_dict(["UseInternalController.k"]).values())[0])
        for controller_name in controller_names:
            controller=get_controller_by_string(controller_name)
            # if model internal heating controller should be used, don't add external heating controllers to list. 
            # criterion to be an external heating controller: output is 'ctrSignalHeating' (heating controller interface of fmu)
            if not(b_internal_heating_controller_active and "ctrSignalHeating" in controller.parameters_u):
                self.controllers.append(controller)
        
        #%%
        self.controller_step_size = controller_step_size

        self.fmu_wrapper = fmu_wrapper

    def configure_controllers(self):
        '''
        Configure external controller instances for the current simulation series.

        This method iterates through the list of previously instantiated external 
        controller class instances and configures each one using the current 
        state of the FMU. The configuration is done by retrieving the control 
        variables specific to each controller.

        '''        
        for controller in self.controllers:
                controller.configure(self.fmu_wrapper.get_fmu_state_dict(controller.get_control_variables()))

    def perform_control_check(self, curr_time_relative):
        '''
        Determines if control action should be performed at the current simulation time.
        Returns a boolean indicating whether the the control action should be performed based on the elapsed simulation time and the `controller_step_size` parameter from the configuration.

        Parameters:
            curr_time_relative (float): The simulation time, elapsed since simulation start time

        Returns:
            bool: True if control action should be performed, False otherwise.
        ''' 
        if any(self.controllers) and curr_time_relative % self.controller_step_size == 0:
            return True
        else:
            return False

    def get_variables_to_read(self):
        '''
        Retrieve all variables from the model needed for calculating control outputs.

        This method collects and returns a list of variables required by the 
        external controllers to compute their respective control outputs.
        '''        
        variables_to_read = []
        for controller in self.controllers:   
            variables_to_read+=controller.get_control_variables() # Read all the controller variables when controller step is needed.
        return variables_to_read

    def handle_control_action(self, curr_time, fmu_state_dict):
        '''
        Handle control action(s) by iterating through the external controllers in use, 
        calculating the control output(s) for each controller based on 
        the current FMU state and applies the outputs to the model.
        '''
        for controller in self.controllers: 
            fmu_state_dict_modified = controller.control(fmu_state_dict=fmu_state_dict, curr_time=curr_time)
            #limit the controller outputs to the intersection of configured controller output variables and 
            # actually returned variables by the controller
            controller_output_keys=set(fmu_state_dict_modified) & set(controller.parameters_u) 
            #multiple output controller
            controller_output={key:fmu_state_dict_modified[key] for key in controller_output_keys}  
            self.fmu_wrapper.alter_in_fmu(controller_output)