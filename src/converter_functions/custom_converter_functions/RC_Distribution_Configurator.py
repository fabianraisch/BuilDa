from src.converter_functions.converter_function import ConverterFunction
import pandas as pd 


class RC_Distribution_Configurator(ConverterFunction):
    '''
    Sets up preconfigured R and C distribution profiles that are part of the definition of the component 
    properties together with U-values and heat capacity (e.g. the wall structure).
    In the configuration file, the profiles for R and C distributions defined in this class can be configured as strings, 
    e.g., monolithic, heavy, lightweight. 
    If configured, the real distribution is identified by the parameter name in the config file and the configured profile name.
    '''
    def __init__(self):
        super().__init__()
        # Definition of RC_distribution_profiles_n3, only use, when number of elements n=3,
        # Groupwise definition of components possible (syntax: "floor|roof|extWall|...")
        self.RC_distribution_profiles_n3={
            "monolythic":{
                "floor|roof|extWall":{"C":[1,1,1],"R":[1,1,1,1]},
                "intWall":{"C":[1,1,1],"R":[1,1,1]}
            },
            #Placement of the capacities always in the middle of the layer (set-up: R1/2-C1-mean(R12)-C2-mean(R23)-C3-R3/2)
            "heavy":{               #from ashrae 140-2004 TC900
                "floor":{"C":[112000,0.001,0.001],"R":[0.000739583333333333, 0.131859375, 0.262239583333333, 0.131119791666667]},
                "roof":{"C":[7980,1126.944,9063],"R":[0.00065625, 0.0297604166666667, 0.0305208333333333, 0.00141666666666667]},
                "extWall":{"C":[140000,861,4293],"R":[0.00154088050314465, 0.013624213836478, 0.0125864779874214, 0.00050314465408805]},
                "intWall":{"C":[1,1,1],"R":[1,1,1]},
            },          
            "lightweight":{        #from ashrae 140-2004 TC600    
                "floor":{"C":[19500,5055.12,5055.12],"R":[0.00186458333333333, 0.132463541666667, 0.261197916666667, 0.130598958333333]},
                "roof":{"C":[7980,1126.944,9063],"R":[0.00065625, 0.0297604166666667, 0.0305208333333333, 0.00141666666666667]},
                "extWall":{"C":[9576,665.28,4293],"R":[0.000589622641509434, 0.013561320754717, 0.0134748427672956, 0.00050314465408805]},
                "intWall":{"C":[1,1,1],"R":[1,1,1]},
            }, 

            #wall constructrion according to: 
            # https://www.ubakus.de/u-wert-rechner/index.php?c=2&M0=132061I1&M1=132153I33&l1=0.23&r1=550&name1=Geschosshohe%20Porenbetonplatten&v1=f2f2f2&tex1=gf&M2=77i5&T_i=20&RH_i=50&Te=-5&RH_e=80&outside=0&bt=0&unorm=enev14alt&cq=2947871&name=AW%20Porenbeton%20Fassadenelemente%20GSB%2035%2C%2033%20cm%2C%20ab%201952&fz=14
            "gasConcrete":{
                "extWall":{"C":[14000, 181500, 6000 ],"R":[0.07, 0.7875, 0.721, 0.0035 ]},
            },

            #wall constructrion according to: 
            # https://www.ubakus.de/u-wert-rechner/index.php?c=2&M0=199i15&M1=132261I24&v1=b7b7b7&tex1=0&M2=133477I2&M3=136921i115&v3=cc5c4a&tex3=vz2&T_i=20&RH_i=50&Te=-5&RH_e=80&outside=0&bt=0&Rsi=U&unorm=enev14alt&cq=2947497&name=AW%20Bims-Schwemmstein%2024%20cm%2C%20Schalenfuge%2FVZ-Vormauer%201200%20kg%2Fm%C2%B3%2C%20ab%201952&fz=14
            "perforatedBrick":{ 
                "extWall":{"C":[167100, 28000, 138000 ],"R":[0.3535, 0.3605, 0.117, 0.11  ]},
            },

            #wall constructrion according to: 
            # https://www.ubakus.de/u-wert-rechner/index.php?c=2&M0=133859i6&M1=36i24&M2=137011i2&M3=86I6&M4=36I9&x4=-0.05&y4=0.2&w4=6&R4=60&M5=132403I3&v5=81674f&tex5=kork&M6=132657i3&M7=90i24&M8=36i24&y8=0&w8=4.8&R8=30&hz8=1&M9=119929i44&T_i=20&RH_i=50&Te=-5&RH_e=80&outside=0&bt=0&unorm=enev14alt&cq=2947513&name=AW%20Einsteins%20Sommerhaus%2C%20Holzrahmen%2012%20cm%2C%203%20cm%20Torfd%C3%A4mmung%2C%201929&fz=14
            "baloonFraming":{ 
                "extWall":{"C":[26880, 2446, 7850],"R":[0.1425, 0.268922018348624, 0.465422018348624, 0.339 ]},
            },
            #Draft for additional distribution profile:
            # // Placement of the innermost capacity in the center of the innermost layer, the rest on the inner side of the resistance. (set-up: R1/2-C1-R1/2-C2-R2-C3-R3)
            #  "extWall_R_distribution":[[0.098,0.098,1.537,0.064], [0.0375,0.0375,1.65,0.064]],  
            #  "floor_R_distribution":[[0.0355, 0.0355, 12.5875, 12.5875], [0.0895,0.0895,12.5375,12.5375]],
            #  "roof_R_distribution":[[0.0315, 0.0315, 2.794, 0.136], [0.0315,0.0315,2.794,0.136]],             
        }

    def convert(self, variable_dict):
        tr=variable_dict
        for k in tr.keys():
            # Check if parameter is a distribution parameter and its value is of type string and if so, treat it as an RC_distribution_profile name
            if k.endswith("_distribution") and type(tr[k]) is str:
                profile=tr[k]
                if profile in self.RC_distribution_profiles_n3.keys():
                    component,part_key,_=k.split("_")
                    # Get correct component_key, also in case if component is defined in group with other components (syntax: "component1|component2|...")
                    component_keys=[k for k in self.RC_distribution_profiles_n3[profile].keys() if component in k.split("|")]
                    if len(component_keys)>1: raise ValueError("Multiple defined profiles for ",profile,component,part_key,"distribution: ",str(component_keys))
                    else: component_key=component_keys[0]
                    
                    tr[k]=self.RC_distribution_profiles_n3[profile][component_key][part_key]
                    ## debug print
                    # print(component,component_key)
                    # print(k,tr[k])
                else:
                    raise KeyError("RC-Distribution-profile '"+profile+"' not found. Available profiles are: "+str(self.RC_distribution_profiles_n3.keys()))
        return tr

