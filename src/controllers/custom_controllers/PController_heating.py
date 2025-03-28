from src.controllers.controller import Controller
from src.controllers.custom_controllers.PIController_heating import PIController_heating


class PController_heating(PIController_heating):  
    '''PController (Proportional Controller): Adjusts the output proportionally to the error, 
    defined as the difference between the desired setpoint and the current process variable y.
    This controller is used for heating.

    Controller algorithm: u(t) = P*e(t) + I*integral(e(t))dt
    '''

    def __init__(self,
                parameters_y="thermalZone.TAir",
                parameters_u=["ctrSignalHeating"],
                parameters_etc=[],
                P=.7, 
                w={0-1:18+273.15,6*3600-1:22+273.15,22*3600-1:18+273.15},   #setpoints for nocturnal decrease from 22 to 6 
                #w=20+273.15, #setpoint if no nocturnal decrease
                I=0,  
                anti_windup=True,
                b_reversed_action_control=False,
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
        self.b_reversed_action_control=b_reversed_action_control
        self.P=P
        self.I=I
        #initialization
        self.integrativePart=0
        self.b_clamping_on=False #actual state of clamping (anti_windup technique)
        self.curr_time_last=0


