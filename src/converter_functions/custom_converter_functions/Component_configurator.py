from src.converter_functions.converter_function import ConverterFunction
import pandas as pd 


class Component_configurator(ConverterFunction):
    '''
    Sets up preconfigured wall construction profiles comprising U-Value, 
    heat capacity and R- and C-distributions.
    Profiles include e.g., 'heavy', 'lightweight',  
        'pumiceAndBrick', 'baloonFraming'
    '''
    def __init__(self):
        super().__init__()
        # Definition of Component_constructions_n3, only use, when number of elements n=3,
        self.Component_constructions_n3={

            "heavy":{               #from ashrae 140-2004 TC900
                "UExt":0.512,
                "heatCapacity_wall":145154,
                "extWall_C_distribution":"heavy",
                "extWall_R_distribution":"heavy", 

                "URoof":0.318,
                "heatCapacity_roof":18169.944,
                "roof_C_distribution":"heavy",
                "roof_R_distribution":"heavy",                
                "UFloor":0.039,
                "heatCapacity_floor":112000.00200000001,
                "floor_C_distribution":"heavy",
                "floor_R_distribution":"heavy",
            },     
            "lightweight":{               #from ashrae 140-2004 TC600
                "UExt":0.514,
                "heatCapacity_wall":14534.28,
                "extWall_C_distribution":"lightweight",
                "extWall_R_distribution":"lightweight",

                "URoof":0.318,
                "heatCapacity_roof":18169.944,
                "roof_C_distribution":"lightweight",
                "roof_R_distribution":"lightweight",                
                "UFloor":0.039,
                "heatCapacity_floor":29610.239999999998,
                "floor_C_distribution":"lightweight",
                "floor_R_distribution":"lightweight",
                
            },       


            #wall constructrion according to: 
            # https://www.ubakus.de/u-wert-rechner/index.php?c=2&M0=132061I1&M1=132153I33&l1=0.23&r1=550&name1=Geschosshohe%20Porenbetonplatten&v1=f2f2f2&tex1=gf&M2=77i5&T_i=20&RH_i=50&Te=-5&RH_e=80&outside=0&bt=0&unorm=enev14alt&cq=2947871&name=AW%20Porenbeton%20Fassadenelemente%20GSB%2035%2C%2033%20cm%2C%20ab%201952&fz=14
            "gasConcrete":{               #from ashrae 140-2004 TC600
                "UExt":0.615,
                "heatCapacity_wall":201500,
                "extWall_C_distribution":"gasConcrete",
                "extWall_R_distribution":"gasConcrete",
            },     


            #wall constructrion according to: 
            # https://www.ubakus.de/u-wert-rechner/index.php?c=2&M0=199i15&M1=132261I24&v1=b7b7b7&tex1=0&M2=133477I2&M3=136921i115&v3=cc5c4a&tex3=vz2&T_i=20&RH_i=50&Te=-5&RH_e=80&outside=0&bt=0&Rsi=U&unorm=enev14alt&cq=2947497&name=AW%20Bims-Schwemmstein%2024%20cm%2C%20Schalenfuge%2FVZ-Vormauer%201200%20kg%2Fm%C2%B3%2C%20ab%201952&fz=14
            "pumiceAndBrick":{ 
                "UExt":0.9,
                "heatCapacity_wall":333100,
                "extWall_C_distribution":"pumiceAndBrick",
                "extWall_R_distribution":"pumiceAndBrick",
            },

            #wall constructrion according to: 
            # https://www.ubakus.de/u-wert-rechner/index.php?c=2&M0=133859i6&M1=36i24&M2=137011i2&M3=86I6&M4=36I9&x4=-0.05&y4=0.2&w4=6&R4=60&M5=132403I3&v5=81674f&tex5=kork&M6=132657i3&M7=90i24&M8=36i24&y8=0&w8=4.8&R8=30&hz8=1&M9=119929i44&T_i=20&RH_i=50&Te=-5&RH_e=80&outside=0&bt=0&unorm=enev14alt&cq=2947513&name=AW%20Einsteins%20Sommerhaus%2C%20Holzrahmen%2012%20cm%2C%203%20cm%20Torfd%C3%A4mmung%2C%201929&fz=14
            "baloonFraming":{ 
                "UExt":0.732,
                "heatCapacity_wall":37176,
                "extWall_C_distribution":"baloonFraming",
                "extWall_R_distribution":"baloonFraming",
            },

            ##Draft for additional Component_constructions_n3 profile:
            # "templateWall":{ 
            #     "UExt":*value_of_template_wall*,
            #     "heatCapacity_wall":*value_of_template_wall*,
            #     "extWall_C_distribution":*C-Distribution_of_template_wall*,
            #     "extWall_R_distribution":*R-Distribution_of_template_wall*,
            #     add other expressions as needed...
            # },
        }

        #add components defined in external files
        import json,glob,os
        for json_file in glob.glob("resources/componentConstructions/*json"):
            new_components=json.load(open(json_file,"r"))
            new_keys=set(new_components.keys()) - set(self.Component_constructions_n3.keys())
            if len(new_keys)==0:
                print(f"Nothing added from file {json_file}, as {list(new_components.keys())} already configured.")
            for key in new_keys:
                self.Component_constructions_n3.update({key:new_components[key]})


    


    def convert(self, variable_dict):
        tr=variable_dict
        for key in tr.keys():
            #check if configured parameter value of parameter key is within the 
            # Component construction profiles, indicating that an existing 
            # profile should be applied for configuration
            if type(tr[key]) is str   and   tr[key] in self.Component_constructions_n3.keys():
                try:
                    #replace formerly configured link to profile by corresponding 
                    # value from profile
                    tr[key]=self.Component_constructions_n3[tr[key]] [key]
                except KeyError:
                    #raises an error, if there is no value for the parameter configured
                    # in profile, except parameter is starting with '#'
                    if not(key.startswith("#")):
                        raise IndexError(f"""Could not read out value for parameter '{key}' on component profile '{tr[key]}'. There is none configured.""")        
        return tr

