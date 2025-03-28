from src.converter_functions.converter_function import ConverterFunction
import pandas as pd 


class Zone_dimensions_calculator(ConverterFunction):
    '''
    Calculate:
        - areas of internal and external walls, roof, floor, windows for each geographical direction
        - weighting factors for windows and walls to calculate the EquivalentAirTemperature according to VDI6007
    Based on:
        - zone length, width and height, number of floor levels, window to wall fraction for each geographical direction
    '''
    def __init__(self):
        super().__init__()

    def convert(self, variable_dict):
        to_return = variable_dict 

        to_return["zone_height"]=to_return["n_floors"]*to_return["floor_height"]
        wall_area_south_north = to_return["zone_length"] * to_return["zone_height"] # Calculation of the wall area for south / north
        wall_area_west_east = to_return["zone_width"] *  to_return["zone_height"]  # Calculation of the wall area for west / east
        wall_area_floor_ceiling = to_return["zone_length"] * to_return["zone_width"] # Calculation of the floor and ceiling area
        zone_volume = to_return["zone_length"] * to_return["zone_width"] * to_return["zone_height"] # Calculation of the zone volume
        to_return["thermalZone.VAir"] = zone_volume * 0.76 # Calculation of the zone air volume (reduction factor 0.76 according to DIN 18599-1)

        to_return["thermalZone.AExt[1]"], to_return["thermalZone.AExt[3]"] = wall_area_south_north, wall_area_south_north  # Assigning the wall area for south / north
        to_return["thermalZone.AExt[2]"], to_return["thermalZone.AExt[4]"] = wall_area_west_east, wall_area_west_east  # Assigning the wall area for west / east
        to_return["thermalZone.AFloor"] = wall_area_floor_ceiling   # Assigning the floor area
        to_return["thermalZone.ARoof"] = wall_area_floor_ceiling * to_return["fARoofToAFloor"]  # Assigning the roof area from the floor area and the ratio factor fARoofToAFloor
        to_return["thermalZone.AInt"]=to_return["fAInt"]  *  (to_return["thermalZone.AExt[1]"] + to_return["thermalZone.AExt[2]"] + to_return["thermalZone.AExt[3]"] +to_return["thermalZone.AExt[4]"])

        to_return["thermalZone.AWin[1]"]=to_return["fAWin_south"]  *  wall_area_south_north
        to_return["thermalZone.AWin[2]"]=to_return["fAWin_west"]  *  wall_area_west_east
        to_return["thermalZone.AWin[3]"]=to_return["fAWin_north"] * wall_area_south_north
        to_return["thermalZone.AWin[4]"]=to_return["fAWin_east"]  *  wall_area_west_east

        # Here, the transparent portion of the window is calculated. 
        to_return["thermalZone.ATransparent[1]"] = to_return["thermalZone.AWin[1]"] * to_return["fATransToAWindow"]  
        to_return["thermalZone.ATransparent[2]"] = to_return["thermalZone.AWin[2]"] * to_return["fATransToAWindow"]  
        to_return["thermalZone.ATransparent[3]"] = to_return["thermalZone.AWin[3]"] * to_return["fATransToAWindow"]  
        to_return["thermalZone.ATransparent[4]"] = to_return["thermalZone.AWin[4]"] * to_return["fATransToAWindow"]  

        to_return["thermalZone.AExt[1]"] =  (to_return["thermalZone.AExt[1]"] - to_return["thermalZone.AWin[1]"])
        to_return["thermalZone.AExt[2]"] =  (to_return["thermalZone.AExt[2]"] - to_return["thermalZone.AWin[2]"])
        to_return["thermalZone.AExt[3]"] =  (to_return["thermalZone.AExt[3]"] - to_return["thermalZone.AWin[3]"])
        to_return["thermalZone.AExt[4]"] =  (to_return["thermalZone.AExt[4]"] - to_return["thermalZone.AWin[4]"])
        
        to_return["wallExt_area_total"] =   to_return["thermalZone.AExt[1]"] + to_return["thermalZone.AExt[2]"] + to_return["thermalZone.AExt[3]"] + to_return["thermalZone.AExt[4]"] # Calculation of the total external wall area (without the window area)
        to_return["win_area_total"] =       to_return["thermalZone.AWin[1]"]  + to_return["thermalZone.AWin[2]"] + to_return["thermalZone.AWin[3]"] + to_return["thermalZone.AWin[4]"] # Calculation of the total window area
        to_return["envelope_area_total"] =  to_return["wallExt_area_total"] + to_return["win_area_total"] + to_return["thermalZone.AFloor"] + to_return["thermalZone.ARoof"] # Calculation of the total area of building envelope

        to_return["eqAirTemp.wfWin[1]"] =  to_return["thermalZone.AWin[1]"] / to_return["win_area_total"] # Calculating weighting factors for windows to calculate the EquivalentAirTemperature according to VDI6007
        to_return["eqAirTemp.wfWin[2]"] =  to_return["thermalZone.AWin[2]"] / to_return["win_area_total"]
        to_return["eqAirTemp.wfWin[3]"] =  to_return["thermalZone.AWin[3]"] / to_return["win_area_total"]
        to_return["eqAirTemp.wfWin[4]"] =  to_return["thermalZone.AWin[4]"] / to_return["win_area_total"]

        to_return["eqAirTemp.wfWall[1]"] =  to_return["thermalZone.AExt[1]"]  / to_return["wallExt_area_total"] # Calculating weighting factors for walls to calculate the EquivalentAirTemperature according to VDI6007
        to_return["eqAirTemp.wfWall[2]"] =  to_return["thermalZone.AExt[2]"]  / to_return["wallExt_area_total"]
        to_return["eqAirTemp.wfWall[3]"] =  to_return["thermalZone.AExt[3]"]  / to_return["wallExt_area_total"]
        to_return["eqAirTemp.wfWall[4]"] =  to_return["thermalZone.AExt[4]"]  / to_return["wallExt_area_total"]
        
        
        return to_return



