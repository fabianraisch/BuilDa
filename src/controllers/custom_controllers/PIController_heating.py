from src.controllers.controller import Controller



class PIController_heating(Controller):  
    '''
    PIController (Proportional-Integral Controller): Adjusts the output based on both 
    the current error and the integral of past errors, providing improved stability and 
    eliminating steady-state error compared to a P-controller.
    This controller is used for heating.

    It also has clamping implemented as an anti-windup technique to prevent excessive 
    accumulation of the integral term.

    Controller algorithm: u(t) = P*e(t) + I*integral(e(t))dt
    '''

    def __init__(self,
                parameters_y="thermalZone.TAir",
                parameters_u=["ctrSignalHeating"],
                parameters_etc=[],
                P=.5, 
                w={0-1:18+273.15,6*3600-1:22+273.15,22*3600-1:18+273.15},   #setpoints for nocturnal decrease from 22 to 6 
                #w={0-1:23+273.15,6*3600-1:22+273.15,22*3600-1:18+273.15},   #setpoints for nocturnal decrease from 22 to 6 
                #w=20+273.15, #setpoint if no nocturnal decrease
                I=.001,  
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
        self.curr_time_last=0
        self.u_last=0

    #called before every step of simulation
    def control(self,fmu_state_dict,curr_time):

        #get possibly scheduled setpoint w
        w=self.get_current_w(curr_time)

        #read out value of control variable y
        y=fmu_state_dict[self.parameters_y]

        #calculate error, also in case of reversed action control
        e=(w-y) *(1 if not(self.b_reversed_action_control) else -1)

        u=e*self.P
        if self.I!=0:
            dt=curr_time-self.curr_time_last

            #clamping: Clamping, or conditional integration, prevents the integral 
            # output from accumulating in the appropriate direction when 
            # the controller output is saturated.
            if (self.u_last>self.u_max and dt*e>0) or (self.u_last<self.u_min and dt*e<0):
                self.integrativePart+=0 #clamping takes effect
            else:
                self.integrativePart+=dt*e #no clamping

            u+=self.integrativePart*self.I
        u_limited=min(max(self.u_min,u),self.u_max)
        fmu_state_dict[self.parameters_u[0]]=float(u_limited)

        self.curr_time_last=curr_time
        self.u_last=u
        return(fmu_state_dict)