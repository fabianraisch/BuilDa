from src.controllers.controller import Controller
from src.controllers.custom_controllers.PIController_heating import PIController_heating

class PIController_cooling(PIController_heating):  
    '''
    PIController (Proportional-Integral Controller): Adjusts the output based on both the current error 
    and the integral of past errors, providing improved stability and 
    eliminating steady-state error compared to a P-controller.

    This controller is used for cooling. Thus the described control action is reversed. 
    It also has clamping implemented as an anti-windup technique to prevent excessive 
    accumulation of the integral term.
    The b_reversed_action_control is set to True to indicate that the controller should be active if 
    the process variable y exceeds the setpoint, rather than when it's below it.

    Controller algorithm: u(t) = P*e(t) + I*integral(e(t))dt
    '''
    def __init__(self,
                parameters_y="thermalZone.TAir",
                parameters_u=["ctrSignalCooling"],
                parameters_etc=[],
                P=.7, 
                w=27+273.15,  #start to cool 27°C upwards
                I=.001,  
                anti_windup=True,
                b_reversed_action_control=True,
                u_max=1,
                u_min=0   
                ):
        super().__init__(
            parameters_y=parameters_y,
            parameters_u=parameters_u,
            parameters_etc=parameters_etc,
            u_max=u_max,
            u_min=u_min,
            w=w
        )
        self.b_reversed_action_control = b_reversed_action_control
        self.P = P
        self.I = I
        # initialization
        self.integrativePart = 0
        self.b_clamping_on = False  # actual state of clamping (anti-windup technique)
        self.curr_time_last = 0