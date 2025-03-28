from src.controllers.controller import Controller



class TwoPointController_heating(Controller):  
    '''
    Two point controller: Operates by switching the output between 0 and 1, 
    turning fully on (1) when y is below the setpoint and fully off (0) 
    when it exceeds the setpoint.

    In this case, it is used for heating. 
    
    The hysteresis parameter defines the range within which the controller will not 
    switch states to prevent rapid cycling.
    '''
    def __init__(self,
                parameters_y="thermalZone.TAir",
                parameters_u=["ctrSignalHeating"],
                parameters_etc=[],
                u_max=1,
                u_min=0,
                hysteresis=0,
                w={0-1:18+273.15,6*3600-1:22+273.15,22*3600-1:18+273.15},   #setpoints for nocturnal decrease from 22 to 6 
                #w=20+273.15, #setpoint if no nocturnal decrease
                b_reversed_action_control=False #default False: negative feedback loop: increasing in control variable leads to decreasing in controller output
                ):
        super().__init__(
            u_max=u_max,
            u_min=u_min,
            parameters_u=parameters_u,
            parameters_y=parameters_y,
            parameters_etc=parameters_etc,
            w=w
        )
        self.hysteresis=hysteresis
        self.b_reversed_action_control=b_reversed_action_control

    #called before every step of simulation
    def control(self,fmu_state_dict,curr_time):

        #get possibly scheduled setpoint w
        w=self.get_current_w(curr_time)
        
        #read out value of control variable y
        y=fmu_state_dict[self.parameters_y]

        #calculate error, also in case of reversed action control
        e=(w-y) *(1 if not(self.b_reversed_action_control) else -1)

        #calculate controller output
        if (e+self.hysteresis)<0: 
            u=self.u_min #lower limit u to u_min
        elif (e-self.hysteresis)>0:  
            u=self.u_max #limit u to u_max
        else: #don't change u
            u=fmu_state_dict[self.parameters_u[0]]

        fmu_state_dict[self.parameters_u[0]]=float(u)
        
        return(fmu_state_dict)

