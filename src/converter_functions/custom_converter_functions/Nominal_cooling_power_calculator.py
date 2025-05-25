import numpy as np
from src.converter_functions.converter_function import ConverterFunction
from src.utils.util_functions import load_hygienicalWindowOpening_data,load_internalGain_data,load_weather_data,df_findcol



class Nominal_cooling_power_calculator(ConverterFunction):
    '''
    A class to calculate the nominal cooling power required for a 
    building based on various parameters including building 
    characteristics and environmental conditions.

    This class is designed to implement the calculation of nominal
     cooling power as per the guidelines established in DIN 18599-2. 
    It takes into account both the internal and external temperature
    settings, as well as heat loss due to ventilation and building 
    materials.

    Note: Some comments reference variable descriptions in the 
    standard, which is why there are mentions of formulas and sections.

    The following assumptions and simplifications have been made:
    
        ---------Assumptions---------
        Assumption: Residential building
        Assumptions: Compliance with the requirements for building 
            tightness according to DIN 4108-7 (i.e., the tightness test 
            is conducted according to the criteria of this standard 
            after completion);
        Assumption: mechanical ventilation system if n > 0.1 (n_inf)
        Assumption: the entire zone envelope area is heat-transmitting (e.g. no adjacent zones)
        Assumption: Operating time of the ventilation system 24 h/d, 
            because a constantly operated system is assumed in the model
        Assumption: 24 h/d in operation (the daily operating duration 
            of the cooling system).
        Assumption: There are no adjacent zones, thus, heat flow to 
            other zones dQ_T_j is assumed to be 0
        Assumption: no internal heat sinks
        Assumption: No detailed building information available; 
            thermal bridge supplement is assumed to 
            ΔUWB = 0.10 W/(m²·K) according to standard
        Assumption: No heat transmission between heated and unheated
             zones
        Assumption: If there is a supply and exhaust air system, then 
            assume the complete air exchange rate as the supply air 
            exchange rate.

        ---------Simplifications---------
        Simplification from standard: Assuming effective wall heat 
            capacity according to building class: light->50 Wh/k, 
            medium-> 90 Wh/K, heavy->130 Wh/k
            -> Own calculation to find out building class (light, 
                medium or heavy), using exemplary wall profiles' heat 
                capacity to compare it with the actual heat capacity of
                the external walls configured in the model
        Simplification/Assumption: Highest daily average of 
            weather data = the average outdoor temperature on the 
            design day according to DIN V 18599-10
        Simplification: maximum hourly average of horizontal global
            radiation from the weather file = the maximum hourly solar 
            radiation on the design day (see DIN V 18599-10);
        Simplification: own calculation based on DIN 18599-10 Table 9: 
            factor to convert global horizontal radiation to radiation
            on vertical surfaces facing south, east, north, west in 
            Germany in the month of July
        Simplification: g-value of the window * reduction factor due 
            to possible shading for calculating the overall energy 
            transmission coefficient including sun protection
        Simplification: Orientation of the roof (cardinal directions) 
            is irrelevant
        Simplification: own calculation, using the mean of the 
            maximum hourly radiation for the roof in the case of 
            roof_angle > 60°
        Simplification: Heat flow through the floor is calculated 
            based on a statically configured floor temperature and cooling 
            setpoint temperature in the model 
            (according to: dQ_T_s=H_T_sdelta_theta_source #Equation C.8)
        Simplification: only distinction between exhaust air and 
            heat recovery system
        Simplification: sum of internal gains from internal gains 
            file is used to represent the internal gains
        Simplification: Interior wall is considered as a simple surface
            between only two building zones
        Simplification: Heat transfer coefficient of floor is only 
            calculated from floor area and U-value of the floor, analogous to H_T_D in 6.2.1
        Simplification from the standard due to the assumption that 
            the ventilation system has no cooling function: For 
            ventilation systems without cooling function and apartment 
            ventilation systems, the uncorrected H θ H ventilation heat
            transfer coefficient of the system air flow is to be used 
            in Equation (135). It applies: H_V_mech_theta=H_V_mech; 
            the temperature-weighted heat transfer coefficient of 
            mechanical ventilation, according to 
            Equations (136) to (138).
    '''

    def __init__(self):
        super().__init__()

    def convert(self, variable_dict):
        #-------------------------------------------------------
        # Setup input variables
        #-------------------------------------------------------
        tr = variable_dict

        weather_data = load_weather_data(tr)
        AExt_list = [tr["thermalZone.AExt[1]"], tr["thermalZone.AExt[2]"], 
                    tr["thermalZone.AExt[3]"], tr["thermalZone.AExt[4]"]]
        AWin_list = [tr["thermalZone.AWin[1]"], tr["thermalZone.AWin[2]"], 
                    tr["thermalZone.AWin[3]"], tr["thermalZone.AWin[4]"]]

        V = tr["thermalZone.VAir"]  # the net room volume

        t_c_op_d = 24  # daily operating time of the cooling system
        delta_theta = 2  # permissible fluctuation of indoor temperature 
                         # (typically 2 K)

        #-------------------------------------------------------
        #calculate effective heat capacity of the building
        #-------------------------------------------------------

        # own calculation: determines whether there is inner insulation on the
        # external walls by comparing the proportion of the innermost 1/4 of 
        # the external wall R-elements to a threshold value
        b_inner_wall_insulation = 0.1 < sum(tr["extWall_R_distribution"] \
                    [:len(tr["extWall_R_distribution"])//4]) / \
                    sum(tr["extWall_R_distribution"])  
        b_high_room = tr["zone_height"] > 4.5

        #%%own calculation of heatCapacity_limits between lightweight, 
        # medium and heavy
        # source of material constants in this 
        # section: https://www.ubakus.de/u-wert-rechner
        # rho_limit*thickness*c_douglas=600 kg/m³*0.1 m *1600 J/(kg*K) 
        # -> density slightly differs from Douglas fir (530 kg/m³) to meet standard
        # conditions
        heatCapacity_limit1 = 600 * 0.1 * 1600  
        # rho_limit*thickness*c_adobe=1600 kg/m³*0.18 m *1600 J/(kg*K) 
        # -> density slightly differs from adobe (1500 kg/m³) to meet standard
        # conditions
        heatCapacity_limit2 = 1600 * 0.18 * 1000  

        A_NGF = tr["thermalZone.AFloor"]
        # simplification from standard: 50: light, 90: medium, 130: heavy 
        # in Wh/K, effective heat capacity of the building zone per 6.7.1
        C_wirk = (50 if (tr["heatCapacity_wall"] < heatCapacity_limit1 or 
                              b_high_room or b_inner_wall_insulation) else 
                  90 if tr["heatCapacity_wall"] < heatCapacity_limit2 else
                 130) * A_NGF  

        #-------------------------------------------------------
        #assumed temperature difference for heat flow into the building
        #-------------------------------------------------------

        # assumption: residential building, maximum allowed indoor 
        # temperature on the design day per DIN V 18599-10
        theta_i_c_max = 26  
        # assumption: residential building, target room 
        # temperature for cooling per DIN V 18599-10
        theta_i_c_soll = 25  
        # design indoor temperature per equation (C.2)
        theta_i = (theta_i_c_max + theta_i_c_soll - 2) / 2  
         # simplification/assumption: highest daily mean from 
         # weather data, external design temperature per DIN V 18599-10
        theta_e_max = df_findcol(weather_data, "dry bulb temperature").\
            resample("1d").mean().max().item() 
        delta_theta_source = max(0, theta_e_max - theta_i)

        #-------------------------------------------------------
        # calculate solar heat gains
        #-------------------------------------------------------

        #%%dQ_S_tr
         # simplification: maximum hourly mean global horizontal radiation 
         # from weather file, max hourly solar radiation on the design day 
         # per DIN V 18599-10
        I_S_max_global_horizontal = df_findcol(weather_data, \
            "global horizontal radiation").\
            resample("1h").mean().max().item() 
        # simplification: own calculation from DIN 18599-10 Table 9, 
        # factor to convert horizontal radiation to vertical (S, E, N, W) 
        # in July
        factor_I_S_max = np.array([605/927, 739/927, 164/927, 739/927])  
        I_S_max_windows = I_S_max_global_horizontal * factor_I_S_max
        A = np.array(AWin_list)  # transparent surface area
         # reduction factor for frame portion, ratio of 
         # transparent area to total glazed unit area, default F=0.7
        F_F = tr["fATransToAWindow"] 
        # residential buildings: 1 (no dirt), reduction 
        # factor due to dirt per DIN V 18599-10
        F_V = 1  
        # own factor for shading device, etc., 
        # to be used when shading is implemented
        factor_shading = 1  
        # simplification: window g-value * shading reduction f
        # actor, total energy transmittance including shading
        g_tot = tr["thermalZone.gWin"] * factor_shading  
        # solar heat gains through transparent components
        dQ_S_tr = sum(A * F_F * F_V * g_tot * I_S_max_windows).item()  

        Rse = tr["Rse_extWall"]  # external heat transfer resistance
        # heat transfer coefficient of component
        U = np.array([tr["UExt"], tr["UExt"], tr["UExt"], tr["UExt"], 
            tr["URoof"]])  
        A = np.array([*AExt_list, tr["thermalZone.ARoof"]])
        alpha = np.array([tr["eqAirTemp.aExt"], tr["eqAirTemp.aExt"], 
            tr["eqAirTemp.aExt"], tr["eqAirTemp.aExt"], 
            tr["eqAirTempVDI.aExt"]])  # solar absorptance of surface
        #own calculation: on a right triangle (roof inclination 45°) the sum 
        # of legs (roof) = sqrt(2)*hypotenuse (floor), when inclination is 
        # higher, then the sum is greater
        F_f_roof=1 if tr["fARoofToAFloor"]>2**.5 else 0.5 
        # simplification: roof orientation irrelevant, 
        # shape factor between component and sky
        F_f = [0.5, 0.5, 0.5, 0.5, F_f_roof]  
        h_r = np.array([tr["eqAirTemp.hRad"], tr["eqAirTemp.hRad"], 
            tr["eqAirTemp.hRad"], tr["eqAirTemp.hRad"], 
            tr["eqAirTempVDI.hRad"]])  # external radiation coefficient
        # simplification from standard: 10 K difference between ambient air and sky temp
        delta_theta_er = 10  
        I_S_max_walls = I_S_max_global_horizontal * factor_I_S_max
        # own calc: roof angle from cosine law and area factor
        roof_angle = (np.pi - 2 * np.arccos(1 - tr["fARoofToAFloor"]**-2)) /\
             2 / np.pi * 180  
        # simplification: use wall radiation for roof if steep
        I_S_max_roof = I_S_max_walls.mean() if roof_angle > 60 else \
            I_S_max_global_horizontal  
        I_S_max_wallsRoof = np.array([*I_S_max_walls, I_S_max_roof])
        dQ_S_opak = sum(Rse * U * A * (alpha * I_S_max_wallsRoof - 
            F_f * h_r * delta_theta_er)).item()
        # total solar heat gains per equations (C.18)–(C.21)
        dQ_S = dQ_S_tr + dQ_S_opak  

        #-------------------------------------------------------
        # calculate transmission heat gain
        #-------------------------------------------------------

        # heat transfer coefficient between cooled zone and outside
        H_T_D = sum(AExt_list) * tr["UExt"] + tr["thermalZone.ARoof"] * \
            tr["URoof"] + sum(AWin_list) * tr["UWin"]  
        dQ_T_e__source = H_T_D * delta_theta_source  # equation C.6

        # simplification: ground heat flow from STATIC model soil 
        # temp and target temp
        dQ_T_s__source = max(0, (tr["TGro.k"] - 273.15) - theta_i) * \
        tr["thermalZone.AFloor"] * tr["UFloor"]  
        # total transmission heat gain if θi,c,max,d < θe,max, 
        # per C.6 and C.8
        dQ_T__source = dQ_T_e__source + dQ_T_s__source  

        #-------------------------------------------------------
        # calculate ventilation heat gains
        #-------------------------------------------------------

        #%%n50
        # if no airtightness test or only planned: use standard values 
        # per Table 7 or Equation (61) with Table 7
        # Table assumptions: Category I: compliance with DIN 4108-7 
        # for airtightness test
        # assumption: mechanical ventilation system if n > 0.1
        b_ventilation_system = tr["airChangeRate"] > .1  
        # assumption: entire zone envelope is heat-transferring surface (e.g. no adjacent zones)
        A_E = sum(AExt_list) + tr["thermalZone.ARoof"] + sum(AWin_list) + \
            tr["thermalZone.AFloor"]  
        # air change at 50 Pa per standard
        n50 =  (1 if b_ventilation_system and V <= 1500 else      
                2 if V <= 1500 else 
                2 * A_E / V if b_ventilation_system else 
                3 * A_E / V)

        # volume flow coefficient, standard value = 0.07, 
        # shielding coefficient per DIN EN ISO 13789
        e = .07  
        # exhaust air system with air transfer devices if no heat recovery
        b_exhaust_air_ventilation_system = b_air_transfer_device = \
            b_ventilation_system and tr["heatRecoveryRate"] == 0  
        # factor for air transfer devices per equations (63) or (64)
        f_ATD = min(16, (n50 - 1.5) / n50) if b_air_transfer_device else 1  

        # coefficient for wind exposure, standard value for moderate shielding
        f = 15  
        # simplification: distinguish between exhaust and HR system
        n_sup = 0 if b_exhaust_air_ventilation_system else 1  
        # simplification: normalized value to differentiate between 
        # full balance and imbalance
        n_eta = 1  
        # eq. 67: factor for increased/decreased infiltration 
        # by mechanical system
        f_e = 1 / (1 + f / e * ((n_eta - n_sup) / (n50 * f_ATD))**2)  
        t_v_mech = 24  # assumption: 24 h/day operation in model
        # eq. 62: infiltration rate with mechanical ventilation
        n_inf = n50 * e * f_ATD * (1 + (f_e - 1) * t_v_mech / 24)  
        c_p_aXrho_a = .34  # set to 0.34 Wh/(m³·K)
        # heat transfer coefficient for infiltration per 6.3.1
        H_V_inf = n_inf * V * c_p_aXrho_a  
        # equation C.13
        dQ_V_inf__source = H_V_inf * delta_theta_source  

        # heat transfer coefficient for window ventilation with 
        # assumed air change n_win = 0.1 h–1
        H_V_win = 0.1 * V * c_p_aXrho_a  
        dQ_V_win__source = H_V_win * delta_theta_source  # equation C.15
        # total ventilation heat gains if θi,c,max,d < θe,max, 
        # per eq. C.13 and C.15
        dQ_V__source = dQ_V_inf__source + dQ_V_win__source  

        #-------------------------------------------------------
        # calculate internal heat gain
        #-------------------------------------------------------
        dQ_I_source = load_internalGain_data(tr).resample("1d").mean().max().item()  # simplification: sum of internal gains from internal gains file
        dQ_source_max = dQ_S + dQ_T__source + dQ_V__source + dQ_I_source  # total heat gains on the design day inside the building zone (power value) per equation (C.3)

        # simplification: sum of internal gains from internal gains file 
        # is used to represent the internal gains
        dQ_I_source = load_internalGain_data(tr).resample("1d").mean().max().item()  

        #-------------------------------------------------------
        # calculate total heat gain
        #-------------------------------------------------------
        # total heat gains on the design day inside the building 
        # zone (power value) per equation (C.3)
        dQ_source_max = dQ_S + dQ_T__source + dQ_V__source + dQ_I_source  


        #-------------------------------------------------------
        # calculate temperature difference for heat sink 
        # calculations
        #-------------------------------------------------------
        delta_theta_sink = max(0, theta_i - theta_e_max)

        #-------------------------------------------------------
        # calculate transmission heat flow out of the building
        #-------------------------------------------------------
        # Heat transmission to the outside, Equation (C.5)
        dQ_T_e__sink = H_T_D * delta_theta_sink  
        # Simplification: Heat flow through the ground is calculated using 
        # the statically configured ground temperature and cooling setpoint 
        # temperature in the model; according to the standard: 
        # dQ_T_s = H_T_s * delta_theta_sink, Equation (C.7)
        dQ_T_s__sink = max(0, theta_i - (tr["TGro.k"] - 273.15)) * \
            tr["thermalZone.AFloor"] * tr["UFloor"]  
        # Assumption: No adjacent zones, thus dQ_T_j = 0; Other transmission 
        # heat flows, 
        # Equation (C.10): dQ_T_j = H_T_j * max(0, theta_i - theta_j)
        dQ_T_j = 0  
        # The sum of the transmission heat sinks when θi,c,max,d > θe,max, 
        # according to Equations (C.5), (C.7), and (C.10)
        dQ_T__sink = dQ_T_e__sink + dQ_T_s__sink + dQ_T_j  

        #-------------------------------------------------------
        # calculate ventilation heat flow out of the building
        #-------------------------------------------------------
        # Heat flow due to infiltration, Equation (C.12)
        dQ_V_inf__sink = H_V_win * delta_theta_sink  
        # Heat flow due to window ventilation, Equation (C.14)
        dQ_V_win__sink = H_V_inf * delta_theta_sink  
        # The sum of ventilation heat sinks when θi,c,max,d > θe,max, 
        # according to Equations (C.12) and (C.14)
        dQ_V__sink = dQ_V_inf__sink + dQ_V_win__sink  

        #-------------------------------------------------------
        # calculate internal heat sink
        #-------------------------------------------------------
        # Assumption: No internal heat sinks; Q_I,sink is the 
        # sum of internal heat sinks according to Equation (C.24)
        dQ_I_sink = 0  

        #-------------------------------------------------------
        # calculate total heat sinks
        #-------------------------------------------------------
        dQ_sink_max = dQ_T__sink + dQ_V__sink + dQ_I_sink  # Equation (C.4)

        #-------------------------------------------------------
        # calculate time constant of the building
        #-------------------------------------------------------
        # Temperature correction factor for calculating the time constant
        # 1 for direct transmission to outside (external components) and 
        # transmission through F = ground according to DIN EN ISO 13370
        Fx_in2out = 1  
        Fx_in2in = 0.5  # for all other components

        # Assumption: No detailed building information available; 
        # thermal bridge supplement; without proof, ΔUWB = 0.10 W/(m²·K) 
        # is generally applied. For external components with internal 
        # insulation and integrated solid ceilings, ΔUWB = 0.15 W/(m²·K)
        delta_U_WB = 0.1  
        # The area of each component that bounds the building zone to outside 
        # air, unheated or uncooled zones, or the ground. For windows and 
        # doors, the clear internal structural opening dimensions are used.
        sum_A_j = sum(AExt_list) + sum(AWin_list) + \
            tr["thermalZone.ARoof"] + tr["thermalZone.AFloor"]  
        # Heat transfer coefficient for 2D thermal bridges
        H_T_WB = sum_A_j * delta_U_WB  
        # Assumption: No heat transfer between heated and 
        # unheated zones; the heat transfer coefficient between 
        # heated and unheated or cooled and uncooled zones according 
        # to Equation (50) or DIN EN ISO 13789 (equivalent to H_D)
        H_T_iu = 0  
        # Simplification: Interior wall is treated as a simple area 
        # between two zones only; heat transfer coefficient between the 
        # zone and the neighboring zone according to Equation (53) or 
        # DIN EN ISO 13789 (equivalent to H_D)
        H_T_iz = tr["UInt"] * tr["thermalZone.AInt"]  
        # Simplification: Calculated only from floor area and U-value 
        # of the floor, analogous to H_T_D in 6.2.1; heat transfer coefficient
        # through the ground (H_T,s corresponds to G according to 
        # DIN EN ISO 13370)
        H_T_s_simplified = tr["thermalZone.AFloor"] * tr["UFloor"]  
        # Sum of the heat transfer coefficients j for all components in the 
        # thermal envelope of the building zone to be included in the 
        # balance according to section 6.2
        sumH_T_j = H_T_D * Fx_in2out + H_T_WB * Fx_in2out + H_T_iu * \
            Fx_in2in + H_T_iz * Fx_in2in + H_T_s_simplified * Fx_in2out  

        #%%sumH_V_k: Sum of ventilation heat transfer coefficients
        # Sum over all ventilation heat transfer coefficients of airflows 
        # entering with outdoor temperature
        sumH_V_k = H_V_inf + H_V_win  

        #%%H_V_mech_theta: Mechanical ventilation
        # Assumption: If a supply and exhaust air system is present, 
        # use total air change rate as supply rate; airflow of the supply air 
        # during system operation according to Equations (92) to (93)
        n_mech_sup = 0 if b_exhaust_air_ventilation_system or not \
            (b_ventilation_system) else tr["airChangeRate"]  
        # Daily average air change rate through mechanical ventilation 
        # according to Equation (90)
        n_mech = n_mech_sup * t_v_mech / 24  
        # Ventilation heat transfer coefficient of mechanical 
        # ventilation (see 6.3.3)
        H_V_mech = n_mech * V * c_p_aXrho_a  
        # Simplification from standard assuming HVAC without cooling 
        # function: For HVAC systems without cooling and residential 
        # ventilation systems, the uncorrected heat transfer coefficient 
        # of the system airflow is used in Equation (135). 
        # Thus: H_V_mech_theta = H_V_mech; temperature-weighted heat transfer 
        # coefficient of mechanical ventilation, according to 
        # Equations (136) to (138)
        H_V_mech_theta = H_V_mech  
        # Total heat transfer coefficient of the building zone, 
        # calculated from transmission and ventilation heat transfer 
        # coefficients according to 5.5.2
        H = sumH_T_j + sumH_V_k + H_V_mech_theta  
        # Time constant of the building zone according to 6.7.2, 
        # but without mechanical ventilation
        tau = C_wirk / H  

        #-------------------------------------------------------
        # calculate cooling demand
        #-------------------------------------------------------
        #%% dQ_c_max: Cooling load
        # Approximate calculation of required maximum cooling 
        # capacity according to Equation (C.1)
        dQ_c_max = 0.8 * (dQ_source_max - dQ_sink_max) * (1 + 0.3 * 
            np.exp(-tau / 120)) - C_wirk / 60 * (delta_theta - 2) + \
                C_wirk / 40 * (12 / t_c_op_d - 1)  
        
        tr["coolingPower"] = dQ_c_max.item()

        return tr