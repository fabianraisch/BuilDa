from src.controllers.controller import Controller
from src.controllers.custom_controllers.TwoPointController_heating import TwoPointController_heating


class TwoPointController_windowOpening(TwoPointController_heating):
    '''
    Two point controller: operates by switching the output between 0 and 1, 
    turning fully on (1) when y is below the setpoint and fully off (0) 
    when it exceeds the setpoint.

    In this case, it is used to simulate window opening when indoor air temperature 
    exceeds the setpoint. Thus the described control action is reversed. 
    The b_reversed_action_control is set to True to indicate that the controller should be active if 
    the process variable y exceeds the setpoint, rather than when it's below it.

    The hysteresis parameter defines the range within which the controller will not 
    switch states to prevent rapid cycling. The b_reversed_action_control is set to True 
    to indicate that the controller should be active if the process variable y exceeds 
    the setpoint, rather than when it's below it.
    '''
    def __init__(self,
        parameters_y="thermalZone.TAir",
        parameters_u=["ctrSignalWindowOpening"],
        parameters_etc=[],
        b_reversed_action_control=True,
        u_max=1,
        u_min=0,
        hysteresis=0,
        w=27+273.15
    ):
        super().__init__(
            parameters_y=parameters_y,
            parameters_u=parameters_u,
            parameters_etc=parameters_etc,
            b_reversed_action_control=b_reversed_action_control,
            u_max=u_max,
            u_min=u_min,
            hysteresis=hysteresis,
            w=w
            )

