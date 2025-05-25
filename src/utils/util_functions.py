import os
import json
import re
import glob
from typing import List
import sys
import os
import pandas as pd



def load_json(path):

    ''' Load the config json file from the filepath.

    Arguments: none.

    Returns:
        the loaded configuration dictionary.
    '''

    to_return = dict()

    #read json file
    json_str_raw=open(path).read()
    #filter c-style comments
    json_str=re.sub(r"//.*","",json_str_raw)
    #parse json string
    to_return = json.loads(json_str)

    #extend wildcard filepaths (if applicable) to plain paths
    for k in to_return["variations"].keys():
        if "fileName" in k:
            paths_total=[]
            paths_unresolved=to_return["variations"][k]
            for path_unresolved in paths_unresolved:
                #use wildcard resolution only if path contains wildcard patterns 
                #(thus, the fmu will still throw an error if a path doesn't exists)
                if "?" in path_unresolved or "*" in path_unresolved:  
                    paths_total+=glob.glob(path_unresolved)
                else: paths_total+=[path_unresolved]
            to_return["variations"][k]=paths_total
    
    #parse time configuration parameters for simulation, if they are in string format
    for time_parameter_key in ["controller_step_size","start_time","stop_time","writer_step_size"]:
        if isinstance(to_return[time_parameter_key],str):
            to_return[time_parameter_key]=parse_duration(to_return[time_parameter_key])
    return to_return


def parse_duration(duration:str)->int:
        '''Parses duration for simulation stop time from strings like 1d, 1y, etc. into seconds.
        
        Parameters:
            - duration (str): duration in string format
        Returns:
            - duration in seconds (int)'''
        factors_str=duration.lower().replace("s",",1").replace("min",",60").replace("h",",3600").replace("d",",86400").replace("w",",604800").replace("y",",31536000").split(",")
        try:
            factors=[float(factor) for factor in factors_str]
            product=factors[0]*factors[1]
        except:
            raise ValueError(f"Time parameter in config JSON in string format which has value '{duration}' cannot be parsed as time period. If parameter is specified in string format, an number followed by one of the units s,min,h,d,w,y should be specified.")
        product=round(product) #only entire seconds
        return product


def get_controller_by_string(s: str):
    '''
    Function to get a certain controller by providing an identifying string.

    Args: 
        - s [str]: strings that identifies the controller needed.

    Returns: The corresponding controller given by the string. If a controller wasn't found, raise error.
    '''
    #%%controllers
    from src.controllers.controller import Controller
    #custom classes
    from src.controllers.custom_controllers.PController_heating import PController_heating
    from src.controllers.custom_controllers.PIController_heating import PIController_heating
    from src.controllers.custom_controllers.TwoPointController_cooling import TwoPointController_cooling
    from src.controllers.custom_controllers.TwoPointController_heating import TwoPointController_heating
    from src.controllers.custom_controllers.TwoPointController_windowOpening import TwoPointController_windowOpening
    from src.controllers.custom_controllers.RandomSchedulePController import RandomSchedulePController
    from src.controllers.custom_controllers.PIController_cooling import PIController_cooling
    if s == "TwoPointController_heating":
        return TwoPointController_heating()
    elif s == "TwoPointController_windowOpening":
        return TwoPointController_windowOpening()
    elif s == "TwoPointController_cooling":
        return TwoPointController_cooling()
    elif s == "PIController_heating":
        return PIController_heating()
    elif s == "PIController_cooling":
        return PIController_cooling()
    elif s == "PController_heating":
        return PController_heating()
    elif s == "RandomSchedulePController":
        return RandomSchedulePController()
    # to add new controller, import class above and insert:
    # elif s == "<my_controller>":
    #     return <my_controller>()

    else:     
        raise ValueError(f"No controller with name {s} found")
    return controllers
        

def get_converter_function_by_string(s: str):
    ''''
    Function to get a certain converter function by providing an identifying string.

    Args:
        - s [str] the string identifying the converter function.

    Returns: A converter function if there exists one with this string.
    '''
    #%%converter functions
    from src.converter_functions.converter_function import ConverterFunction
    #custom classes
    from src.converter_functions.custom_converter_functions.Component_properties_calculator import Component_properties_calculator
    from src.converter_functions.custom_converter_functions.Link_resolver import Link_resolver
    from src.converter_functions.custom_converter_functions.Miscellaneous_handler import Miscellaneous_handler
    from src.converter_functions.custom_converter_functions.Model_compatibility_layer import Model_compatibility_layer
    from src.converter_functions.custom_converter_functions.Nominal_heating_power_calculator import Nominal_heating_power_calculator
    from src.converter_functions.custom_converter_functions.Nominal_cooling_power_calculator import Nominal_cooling_power_calculator
    from src.converter_functions.custom_converter_functions.RC_Distribution_Configurator import RC_Distribution_Configurator
    from src.converter_functions.custom_converter_functions.Zone_dimensions_calculator import Zone_dimensions_calculator
    if s == "Link_resolver":
        return Link_resolver()
    if s == "Miscellaneous_handler":
        return Miscellaneous_handler()
    if s == "Zone_dimensions_calculator":
        return Zone_dimensions_calculator()
    if s == "Component_properties_calculator":
        return Component_properties_calculator()
    if s == "Nominal_heating_power_calculator":
        return Nominal_heating_power_calculator() 
    if s == "Nominal_cooling_power_calculator":
        return Nominal_cooling_power_calculator()
    if s == "RC_Distribution_Configurator":
        return RC_Distribution_Configurator()
    if s == "Model_compatibility_layer":
        return Model_compatibility_layer()
    # to add new converter function, import class above and insert:
    # elif s == "<my_converter_function>":
    #     return <my_converter_function>()

    raise ValueError(f"No converter function with name {s} found")


def get_step_size_arr(start_time, stop_time, writer_step_size, controller_step_size, max_permitted_time_step):
    '''
    Generates a list halting points for the simulation.

    This function computes the halting points in the simulation based on 
    the specified writing intervals and external controller input intervals. 
    It returns a list of step widths between consecutive halting points.

    Parameters:
        start_time (int): The start time of the simulation.
        stop_time (int): The end time of the simulation.
        writer_step_size (int): The time interval for writing output.
        controller_step_size (int): The time interval for external controller input.
        max_permitted_time_step (int): This parameter defines the maximum allowable 
            time step, expressed in seconds, that is consistent with the resolution 
            of the external input files. It ensures that the time intervals between 
            solver steps do not exceed this threshold, thereby ensuring, that all 
            events defined by the external input files are seen by the model. 
            In contrast to writer_step_size, it doesn't affect the the ability for events
            to be seen by the user in the results.
    Returns:
        list: A list of step widths between sorted halting points.

    Raises:
        ValueError: If start_time is greater than stop_time or if step sizes are non-positive.
    '''
    writer_halting_point_array = [i for i in range(start_time, stop_time + 1, writer_step_size)]
    controller_halting_point_array = [i for i in range(start_time, stop_time + 1, controller_step_size)]
    if max_permitted_time_step < min(writer_step_size, controller_step_size):
        required_halting_point_array=[i for i in range(start_time,stop_time+1, max_permitted_time_step)]
        print(f"##Creating additional halting points because max_permitted_time_step(={max_permitted_time_step} s, based on model input files) is smaller than writer_step_size and controller_step_size")
    else:
        required_halting_point_array=[]
    halting_point_set = set(writer_halting_point_array) | set(controller_halting_point_array) | set(required_halting_point_array)
    sorted_halting_point_list = sorted(list(halting_point_set))
    step_list = [sorted_halting_point_list[i] - sorted_halting_point_list[i-1] for i in range(1, len(sorted_halting_point_list))]

    return step_list


def setup_paths(user_config:dict):
    '''
    Sets up paths for the configuration file, FMU, and output directory.

    Parameters:
        user_config (dict): A dictionary containing user-defined configuration parameters.

    Returns:
        - config_path (str): The path to the configuration JSON file.
        - fmu_path (str): The path to the FMU file.
        - output_path (str): The path to the output directory.

    Raises:
        OSError: If no FMU is defined for the current operating system.
    '''
    try:
        config_path = [parameter for parameter in sys.argv[1:] if parameter.lower().endswith(".json")][0]
    except IndexError:
        config_path = os.path.join("resources","configurations", user_config["config_name"])

    try:
        fmu_path = [parameter for parameter in sys.argv[1:] if parameter.lower().endswith(".fmu")][0]
    except IndexError:
        if sys.platform=="win32":   fmu_name=user_config["fmu_name_windows"]
        elif sys.platform=="linux": fmu_name=user_config["fmu_name_linux"]
        
        else: raise OSError("no FMU defined for OS "+str(sys.platform))
        fmu_path=os.path.join("resources","FMUs",fmu_name)

    try:
        output_path = [parameter for parameter in sys.argv[1:] if not(parameter.lower().endswith(".json") or parameter.lower().endswith(".fmu")) ][0]
    except IndexError:
        output_path = user_config["output_path"]

    return config_path, fmu_path, output_path


def load_weather_data(tr):
    '''
    Load weather data from a Modelica weather file.

    Parameters:
    tr (dict): A dictionary containing the key 'weaDat.fileName' with the path to the weather data file.

    Returns:
    pd.DataFrame: A DataFrame with weather data, indexed by time starting from January 1, 2025, 
                and columns named according to the file header.
    '''
    fname=tr["weaDat.fileName"]
    if isinstance(fname,list): fname=fname[0]
    header=open(fname,"r").read().split("\n")[11:40]
    df=pd.read_csv(fname, sep='\t', decimal='.', skiprows=40,header=None,index_col=0).iloc[:,0:29]
    df.columns=header
    df.index=pd.to_timedelta(df.index,unit="s")+pd.to_datetime("2025-1-1")
    return df

def load_internalGain_data(tr):
    '''
    Load internal gain data from a specified file.

    Parameters:
    tr (dict): A dictionary containing the key 'internalGain.fileName' with the path to the internal gain data file.

    Returns:
    pd.DataFrame: A DataFrame with internal gain data, indexed by time starting from January 1, 2025.
    '''
    fname=tr["internalGain.fileName"]
    if isinstance(fname,list): fname=fname[0]
    df=pd.read_csv(fname,sep="\t",skiprows=[1],index_col=0)
    df.index=pd.to_timedelta(df.index,unit="h")+pd.to_datetime("2025-1-1")
    return df

def load_hygienicalWindowOpening_data(tr):
    '''
    Load hygienicalWindowOpening data from a specified file.

    Parameters:
    tr (dict): A dictionary containing the key  'hygienicalWindowOpening.fileName' with the path to the internal gain data file.

    Returns:
    pd.DataFrame: A DataFrame with hygienicalWindowOpening data, indexed by time starting from January 1, 2025.
    '''
    fname=tr["hygienicalWindowOpening.fileName"]
    if isinstance(fname,list): fname=fname[0]
    df=pd.read_csv(fname,sep="\t",skiprows=[1],index_col=0)
    df.index=pd.to_timedelta(df.index,unit="min")+pd.to_datetime("2025-1-1")
    return df

def df_findcol(df,sstr,b_ignorecase=True):
    '''
    Search for columns in a pandas DataFrame that match a specified search string.

    Parameters:
    df (pd.DataFrame): The DataFrame to search within.
    sstr (str): The search string to match against column names.
    b_ignorecase (bool): If True, the search will be case-insensitive; otherwise, it will be case-sensitive.

    Returns:
    pd.DataFrame: A DataFrame containing only the columns that match the search string.
    '''
    return df.loc[:,df.columns.str.contains(sstr,case=not(b_ignorecase))]