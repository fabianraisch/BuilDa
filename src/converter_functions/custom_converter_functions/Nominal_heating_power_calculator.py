from src.converter_functions.converter_function import ConverterFunction
import pandas as pd 


class Nominal_heating_power_calculator(ConverterFunction):
    '''
    A class to calculate the nominal heating power required for a building based on 
    various parameters including building characteristics and environmental conditions.

    This class is designed to implement the calculation of nominal heating power as per 
    the guidelines established in DIN 18599-2. 
    It takes into account both the internal and external temperature settings, 
    as well as heat loss due to ventilation and building materials.
    '''
    def __init__(self):
        super().__init__()

    def convert(self, variable_dict):
        to_return = variable_dict
        
        #%% For the calculation of the nominal heating power according to DIN 18599-2, 
        # the normal outside temperatures according to DIN/TS 12831-1 from April 2020 
        # and the zone temperature should be used. 
        # However, no explicit values are available for all locations - therefore, there are two solutions: 
        #%% 1. Explicitly configure normal outside temperature and zone temperature in the config file 
        # 2. Estimating parameters based on the weather file and from roomTemperatureUpperSetpoint 
        # behavior, if parameters are explicitly set to null in the config file.

        temp_inside=to_return["ti_set"] if to_return["ti_set"]!=None else to_return["roomTempUpperSetpoint"]
        temp_outside=to_return["ta_min"] if to_return["ta_min"]!=None else float(pd.read_csv(to_return["weaDat.fileName"], sep='\t', decimal='.', skiprows=40).iloc[:,1].min())

        fk=0.6 # reduction factor against soil fk = 0.6 according to DIN 4108-6
        c_rho_air=0.34 # product of specific heat capacity and density of air in Wh/(m³*K), according to DIN 18599-2

        # calculate ventilation heat losses
        if all(type(param) is not list for param in [to_return["heatRecoveryRate"], to_return["airChangeRate"], to_return["thermalZone.VAir"]]):
            ventilationHeatLosses = (1 - to_return["heatRecoveryRate"]) * to_return["airChangeRate"] * (to_return["thermalZone.VAir"]) * c_rho_air  # Calculation of the reciprocal of the ventilation heat transfer coefficient H_v in W/K, 
        else:
            ventilationHeatLosses = 0

        # Calculation of the nominal heating load
        # Calculate the reciprocals for each list
        product = to_return["UExt"] * to_return["wallExt_area_total"] + to_return["UWin"] * to_return["win_area_total"] + to_return["UFloor"] * to_return["thermalZone.AFloor"] * fk + to_return["URoof"] * to_return["thermalZone.ARoof"]
        product = product + ventilationHeatLosses # Add ventilation heat losses

        # Calculate the element-wise sum of the reciprocals
        to_return["heatingPower"] = (temp_inside-temp_outside) * product
        
        return to_return





