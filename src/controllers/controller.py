from abc import ABC
import bisect


class Controller(ABC):
    '''
    Abstract base class for custom controllers. It provides basic controller class variables and settings, 
    as well as fundamental functions for all controller classes. 

    Note: It does not provide a working control function; this must be implemented in a custom controller class.
    '''
    def __init__(self,parameters_y="thermalZone.TAir",parameters_u="ctrSignalHeating",parameters_etc=[],w=20,u_min=0,u_max=1):         
        self.parameters_y=parameters_y
        self.parameters_u=parameters_u
        self.parameters_etc=parameters_etc
        self.w=w
        self.u_max=u_max
        self.u_min=u_min

    def configure(self,fmu_state_dict):
        """
        Configure the Controller object based on the FMU state.

        This method performs additional configuration tasks after class instantiation,
        e.g. resolving linked boundary conditions (limits) for the controller.

        Parameters:
        fmu_state_dict (dict): Dictionary containing the FMU state variables.
        """
        #get possibly linked boundary conditions (limits)
        self.w=self.resolve_link_to_fmu_variable(fmu_state_dict=fmu_state_dict,variable=self.w)
        self.u_max=self.resolve_link_to_fmu_variable(fmu_state_dict=fmu_state_dict,variable=self.u_max)
        self.u_min=self.resolve_link_to_fmu_variable(fmu_state_dict=fmu_state_dict,variable=self.u_min)
    

    def control(self, fmu_state_dict: dict, curr_time: int) -> dict:
        '''
        Control function (to override) receiving a dict describing the current FMU state (key -> name of the parameter, value -> value of the parameter).
        This function only contains the logic of the controller and returns the changes in another dict.

        Args:
            - fmu_state_dict [dict]: Dict describing the current state of the FMU
            - curr_time [int]: Integer representing the current simulation time in seconds

        Returns: Dict containing changes that will be made to the FMU.
        '''

        return NotImplementedError("Function control not implemented in this controller. Please override this method first.")
    

    def get_control_variables(self):
         '''
         Function to get all the (control) variables the controller needs in its control function to work properly.
         the variables need to be specified in the class' constructor that inherits from this abstract base class.
         In case there are variables the control method needs in its fmu_state_dict, but they are not given in the control variables list, an error will be thrown.

         Args: None

         Returns: A list of all the variable names needed for controlling.
         '''
         return self.parameters_y, *self.parameters_u, *self.parameters_etc
    
    def get_current_w(self,curr_time):
        """
        Get the current value for w.

        If w is a dictionary (indicating a scheduled value), the method retrieves
        the value corresponding to the current second of the day.

        Parameters:
        curr_time (int): The current time in seconds.

        Returns:
        float: The current value of w.
        """            
        w=self.w
        if type(w) is dict: 
            second_of_day=curr_time%86400
            w_dict=self.w
            w_dict_keys_list=list(w_dict.keys())
            w_dict_keys_list.sort()
            w=w_dict[w_dict_keys_list[bisect.bisect_left(w_dict_keys_list,second_of_day)-1]]
        return w

    def resolve_link_to_fmu_variable(self,fmu_state_dict,variable):
        """
        Resolve a variable name to its value in the FMU state dictionary.

        Parameters:
        fmu_state_dict (dict): Dictionary of state variables.
        variable (str): Variable name to resolve.

        Returns:
        The associated value if found in fmu_state_dict.keys(); otherwise the variable is probably a simple value and the variable is returnd unchanged.
        """        
        if type(variable) is str and variable in fmu_state_dict.keys():
            return fmu_state_dict[variable]
        else: 
            return variable

    
