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
        self.controllers=[]
        self.controllers = get_controller_by_string(controller_names)

        # if model internal heating controller should be used, delete all heating controllers from list. 
        # criterion: output is 'ctrSignalHeating' (heating controller interface of fmu)
        if list(fmu_wrapper.get_fmu_state_dict(["UseInternalController.k"]).values())[0]: 
            self.controllers=[c for c in self.controllers if "ctrSignalHeating" in c.parameters_u]
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

    def perform_control_check(self, curr_time):
        '''
        Determine if a control action should be performed at the current time step.

        This method returns a boolean indicating whether control actions are 
        triggered based on the current time and the specified controller step size.
        '''        
        if any(self.controllers) and curr_time % self.controller_step_size == 0:
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
            controller_output={key:fmu_state_dict_modified[key] for key in controller.parameters_u}  #multiple output controller
            self.fmu_wrapper.alter_in_fmu(controller_output)