from src.controllers.controller import Controller
from src.controllers.custom_controllers.PController_heating import PController_heating
import random

class RandomSchedulePController(PController_heating):  
    '''
    Adjusts the output proportionally to the error, 
    defined as the difference between the desired setpoint and the current process variable y.

    This controller is used for heating.

    Special feature: The setpoint for night (10 p.m. to 6 a.m.) and day (6 a.m. to 10 p.m.) is 
    randomly calculated within a defined range at the instantiation of the controller class.

    Controller algorithm: u(t) = P*e(t) + I*integral(e(t))dt
    '''
    
    def __init__(self):
        super().__init__()
        random.seed(1) 
        temp_setpoint_higher=random.choice([x/100 for x in range(round((20)*100),round((24.5)*100),50)])
        temp_setpoint_dt_higher_lower=0
        if random.random()<=.7: #only 70% of the configurations should have nocturnal decrease at all
            temp_setpoint_dt_higher_lower=random.choice([x/10 for x in range(5,45,5)])
        temp_setpoint_lower=temp_setpoint_higher-temp_setpoint_dt_higher_lower
        self.w={0-1:temp_setpoint_lower,6*3600-1:temp_setpoint_higher,22*3600-1:temp_setpoint_lower}   #nocturnal decrease from 22 to 6 
        self.P=1
        self.I=0
        self.parameters_u = ["ctrSignalHeating", "roomTempUpperSetpoint"]  # roomTempUpperSetpoint is used to store variable setpoint as simulation output; it is normally used for the internal controller, but the use of internal and external controllers is mutually exclusive.

    #called before every step of simulation
    def control(self,fmu_state_dict,curr_time):

        #get possibly scheduled setpoint w
        w=self.get_current_w(curr_time)

        #read out value of control variable y
        y=fmu_state_dict[self.parameters_y]-273.15

        #calculate error, also in case of reversed action control
        e=(w-y) *(1 if not(self.b_reversed_action_control) else -1)

        u=e*self.P
        if self.I!=0 and not(self.b_clamping_on):
            dt=curr_time-self.curr_time_last
            i=dt*e
            self.integrativePart+=i
            u+=self.integrativePart*self.I
        u_limited=min(max(self.u_min,u),self.u_max)
        if u!=u_limited: self.b_clamping_on=True 
        else: self.b_clamping_on=False
        u=u_limited

        fmu_state_dict[self.parameters_u[0]]=float(u)
        fmu_state_dict[self.parameters_u[1]]=float(w)-273.15 #write in fmu for the setpoint w to be stored as timeseries in simulation output
        return(fmu_state_dict)



