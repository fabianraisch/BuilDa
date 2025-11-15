import numpy as np
from src.converter_functions.converter_function import ConverterFunction
from src.utils.util_functions import load_hygienicalWindowOpening_data,load_internalGain_data,load_weather_data,df_findcol



class Nominal_cooling_power_calculator(ConverterFunction):
    '''
"""
    A class to calculate the nominal cooling power required for a building based on various 
    parameters including building characteristics and environmental conditions.

    This class is designed to implement the calculation of nominal cooling power as per the 
    guidelines established in DIN 18599-2. It takes into account both the internal and external 
    temperature settings, as well as heat loss due to ventilation and building materials.

    While the standard DIN 18599-2 is mainly used for the calculation, DIN 18599-10 is 
    sometimes used (as indicated in comments), for specific reference values.
    Other standards might be referenced in the comments as their methodologies have
    been incorporated into the DIN 18599-2 standard.

    Note: Some comments refer to variable descriptions in the standard, which is why there are 
    mentions of formulas and sections.

    --------- Assumptions ---------

    - The building is assumed to be a residential building.
    - Building tightness meets the requirements of DIN 4108-7, meaning a tightness test is 
      performed after completion as per the standard.
    - A mechanical ventilation system is assumed if the infiltration rate n > 0.1 h⁻¹.
    - The entire zone envelope is assumed to be heat-transmitting (i.e., there are no adjacent 
      zones).
    - The ventilation system is assumed to operate continuously (24 h/day).
    - The cooling system is assumed to operate continuously (24 h/day).
    - No heat exchange with adjacent zones: dQ_T_j = 0.
    - No internal cold sinks are present.
    - In the absence of detailed construction data, a thermal bridge supplement of 
      ΔUWB = 0.10 W/(m²·K) is assumed, as per DIN 18599-2, C.3.5.
    - No heat transfer occurs between heated and unheated zones.
    - If a supply and exhaust air system is used, the full air exchange rate is assumed to be 
      supply air.

    --------- Simplifications ---------

    - Building classification (light, medium, heavy) is done via comparison of configured wall 
      heat capacity with typical values:
          - Light: 50 Wh/K
          - Medium: 90 Wh/K
          - Heavy: 130 Wh/K
      (Own calculation based on comparison with DIN 18599-1:2018-09, Table 9 and Annex C; replaces 
      detailed envelope composition.)

    - The highest daily average outdoor temperature from weather data is used as the design day 
      temperature.
      (Simplification from DIN 18599-10, Annex B/C: replaces fixed values from Table B.1 for German 
      locations.)

    - The maximum hourly average of horizontal global radiation from the weather file is used as 
      the peak solar input on the design day.
      (Simplification from DIN 18599-10, where standardized radiation data for the design day are 
      provided per location.)

    - Radiation on vertical façades (S/E/N/W) is estimated using directional conversion factors.
      (Own calculation based on DIN 18599-10, Table 9: directional factor method replaces detailed 
      solar geometry.)

    - Total solar energy transmittance through windows is computed as:  
      g-value x shading reduction factor (F_sh).
      (Own combination; simplified from full solar transmission model in DIN 18599-2, 
      Section 6.3.4.3.)

    - Roof orientation is ignored.
      (Simplification: assumes that directional effects are negligible for averaged high-angle 
      roofs; not modeled in standard.)

    - For roofs with angle > 60°, the mean of max hourly solar radiation is used.
      (Own approximation; replaces incident-angle-specific radiation model from DIN 18599-10, 
      Annex C.)

    - Heat flow through the floor is calculated using:  
      dQ_T_s = H_T_s x Δθ_source
      (Own implementation based on DIN 18599-2, Equation C.8; uses fixed soil temperature.)

    - Only two ventilation system types are modeled:
          - Exhaust air systems
          - Systems with heat recovery
      (Simplification: omits bypass modes or dynamic control as per DIN 18599-2, Section 6.4.)

    - Internal gains are taken from a static input file and summed.
      (Simplification: replaces time- and zone-resolved internal gain modeling in DIN 18599-2, 
      Section 6.5.)

    - Interior walls are modeled as simple planar surfaces between zones.
      (Simplification: neglects 3D effects and junction details not covered in simplified models.)

    - Heat transfer coefficient of the floor is calculated from U-value and area only.
      (Own simplification based on DIN 18599-2, Section 6.2.1; neglects thermal bridging and 
      structural edge effects.)

    - For ventilation systems without cooling function,  
      H_V_mech_theta = H_V_mech is assumed.
      (Simplified application of DIN 18599-2, Equation (135), using uncorrected mechanical 
      ventilation coefficient as per Equations (136-138).)
"""

    '''

    def __init__(self):
        super().__init__()

    def convert(self, variable_dict):
        # -------------------------------------------------------
        # Setup input variables
        # -------------------------------------------------------
        tr = variable_dict

        weather_data = load_weather_data(tr)

        # External wall areas by orientation (indices 1 to 4)
        AExt_list = [
            tr["thermalZone.AExt[1]"],
            tr["thermalZone.AExt[2]"],
            tr["thermalZone.AExt[3]"],
            tr["thermalZone.AExt[4]"]
        ]

        # Window areas by orientation (indices 1 to 4)
        AWin_list = [
            tr["thermalZone.AWin[1]"],
            tr["thermalZone.AWin[2]"],
            tr["thermalZone.AWin[3]"],
            tr["thermalZone.AWin[4]"]
        ]

        V = tr["thermalZone.VAir"]  # Net room volume in m³

        t_c_op_d = 24  # Daily operating time of the cooling system (hours)
        delta_theta = 2  # Allowed indoor temperature fluctuation (typically 2 K)

        # -------------------------------------------------------
        # Calculate effective heat capacity of the building
        # -------------------------------------------------------

        # Determine presence of inner insulation on external walls:
        # Compare proportion of innermost quarter of the external wall's R-values 
        # to threshold (0.1) (own calculation)
        b_inner_wall_insulation = (
            0.1 < sum(tr["extWall_R_distribution"][:len(tr["extWall_R_distribution"]) // 4])
            / sum(tr["extWall_R_distribution"])
        )

        # Flag if room height is considered high (> 4.5 m)
        b_high_room = tr["zone_height"] > 4.5

        # --------------------------------------------------------------------
        # Calculation of heat capacity limits between lightweight, medium, 
        # and heavy constructions (own calculation)
        #
        # Material constants source: https://www.ubakus.de/u-wert-rechner
        #
        # Calculation examples:
        # Douglas fir: density ≈ 600 kg/m³, thickness 0.1 m, specific heat 1600 J/(kg*K)
        # heatCapacity_limit1 = 600 * 0.1 * 1600 = 96000 J/(m²*K)
        #
        # Adobe: density ≈ 1600 kg/m³, thickness 0.18 m, specific heat 1000 J/(kg*K)
        # heatCapacity_limit2 = 1600 * 0.18 * 1000 = 288000 J/(m²*K)
        # --------------------------------------------------------------------

        heatCapacity_limit1 = 600 * 0.1 * 1600
        heatCapacity_limit2 = 1600 * 0.18 * 1000

        A_NGF = tr["thermalZone.AFloor"]

        # Effective heat capacity per DIN 18599-2 (Section 6.7.1), simplified as:
        # Light: 50 Wh/K, Medium: 90 Wh/K, Heavy: 130 Wh/K per floor area
        C_wirk = (
            50 if (tr["heatCapacity_wall"] < heatCapacity_limit1 or b_high_room or
                b_inner_wall_insulation)
            else 90 if tr["heatCapacity_wall"] < heatCapacity_limit2
            else 130
        ) * A_NGF


        #-------------------------------------------------------
        # Calculate the temperature difference for heat flow into the building
        #-------------------------------------------------------

        theta_i_c_max = 26  # residential building is assumed; maximum allowed indoor
                            # temperature on design day (assumption)
        theta_i_c_soll = 25 # residential building is assumed; target room temperature
                            # for cooling (assumption)

        # design indoor temperature per Equation C.2
        theta_i = (theta_i_c_max + theta_i_c_soll - 2) / 2  

        # highest daily mean outdoor temperature from weather data (DIN V 18599-10)
        # (simplification)
        theta_e_max = (
            df_findcol(weather_data, "dry bulb temperature")
            .resample("1d")
            .mean()
            .max()
            .item()
        ) 

        delta_theta_source = max(0, theta_e_max - theta_i)

        #-------------------------------------------------------
        # Calculate solar heat gains
        #-------------------------------------------------------

        # maximum hourly mean global horizontal radiation from weather file (DIN V
        # 18599-10) (simplification)
        I_S_max_global_horizontal = (
            df_findcol(weather_data, "global horizontal radiation")
            .resample("1h")
            .mean()
            .max()
            .item()
        )

        # factor to convert horizontal radiation to vertical (S, E, N, W) in July
        # (own calculation based on DIN 18599-10 Table 9) (simplification)
        factor_I_S_max = np.array([605/927, 739/927, 164/927, 739/927])

        I_S_max_windows = I_S_max_global_horizontal * factor_I_S_max
        A = np.array(AWin_list)  # transparent surface area

        # reduction factor for frame portion, ratio of transparent area to total glazed
        # unit area, default F=0.7 (assumption)
        F_F = tr["fATransToAWindow"] 

        F_V = 1  # dirt reduction factor assumed as 1 for residential buildings (assumption)

        factor_shading = 1  # factor of 1 is assumed for shading devices (assumption)

        # window g-value multiplied by shading reduction factor, total energy transmittance
        # including shading (simplification)
        g_tot = tr["thermalZone.gWin"] * factor_shading  

        # solar heat gains through transparent components
        dQ_S_tr = sum(A * F_F * F_V * g_tot * I_S_max_windows).item()

        Rse = tr["Rse_extWall"]  # external heat transfer resistance

        # heat transfer coefficients of components
        U = np.array([tr["UExt"], tr["UExt"], tr["UExt"], tr["UExt"], tr["URoof"]])
        A = np.array([*AExt_list, tr["thermalZone.ARoof"]])
        alpha = np.array([
            tr["eqAirTemp.aExt"], tr["eqAirTemp.aExt"], tr["eqAirTemp.aExt"],
            tr["eqAirTemp.aExt"], tr["eqAirTempVDI.aExt"]
        ])  # solar absorptance of surfaces

        # Calculation of roof shape factor:
        # For a right triangle roof with 45° inclination, the total projected surface
        # area of roof planes corresponds to sqrt(2) times the floor area.
        # For steeper inclinations, this factor increases accordingly. (own calculation)
        F_f_roof = 1 if tr["fARoofToAFloor"] > 2**0.5 else 0.5  

        # shape factor between component and sky, roof orientation irrelevant (simplification)
        F_f = [0.5, 0.5, 0.5, 0.5, F_f_roof]  

        h_r = np.array([
            tr["eqAirTemp.hRad"], tr["eqAirTemp.hRad"], tr["eqAirTemp.hRad"],
            tr["eqAirTemp.hRad"], tr["eqAirTempVDI.hRad"]
        ])  # external radiation coefficient

        delta_theta_er = 10  # temperature difference between ambient air and sky temperature
                            # (simplification)

        I_S_max_walls = I_S_max_global_horizontal * factor_I_S_max

        # roof angle calculation using cosine law and area ratio (own calculation)
        roof_angle = (np.pi - 2 * np.arccos(1 - tr["fARoofToAFloor"]**-2)) / 2 / np.pi * 180

        # use mean wall radiation for roof if steep (simplification)
        I_S_max_roof = I_S_max_walls.mean() if roof_angle > 60 else I_S_max_global_horizontal

        I_S_max_wallsRoof = np.array([*I_S_max_walls, I_S_max_roof])

        dQ_S_opak = sum(
            Rse * U * A * (alpha * I_S_max_wallsRoof - F_f * h_r * delta_theta_er)
        ).item()

        # total solar heat gains per Equations C.18–C.21
        dQ_S = dQ_S_tr + dQ_S_opak

        #-------------------------------------------------------
        # Calculate transmission heat gain
        #-------------------------------------------------------

        # Determine heat transfer coefficient between cooled zone and outside
        H_T_D = sum(AExt_list) * tr["UExt"] + tr["thermalZone.ARoof"] * \
            tr["URoof"] + sum(AWin_list) * tr["UWin"]  
        dQ_T_e__source = H_T_D * delta_theta_source  # Equation C.6

        # Calculate ground heat flow from STATIC model soil temperature 
        # and target temperature (simplification)
        dQ_T_s__source = max(0, (tr["TGro.k"] - 273.15) - theta_i) * \
            tr["thermalZone.AFloor"] * tr["UFloor"]  

        # Sum transmission heat gains if θi,c,max,d < θe,max, per C.6 and C.8
        dQ_T__source = dQ_T_e__source + dQ_T_s__source  


        #-------------------------------------------------------
        # Calculate ventilation heat gains
        #-------------------------------------------------------

        #%%n50
        # Use standard values per Table 7 or Equation 61 with Table 7
        # if no airtightness test is available or only planned
        # Table assumptions: Category I with compliance to DIN 4108-7 for airtightness (assumption)
        # Assume mechanical ventilation system if n > 0.1 (assumption)
        b_ventilation_system = tr["airChangeRate"] > .1  

        # Assume entire zone envelope is heat-transferring surface (e.g. no adjacent zones) (assumption)
        A_E = sum(AExt_list) + tr["thermalZone.ARoof"] + sum(AWin_list) + \
            tr["thermalZone.AFloor"]  

        # Calculate air change at 50 Pa based on standard
        n50 =  (1 if b_ventilation_system and V <= 1500 else      
                2 if V <= 1500 else 
                2 * A_E / V if b_ventilation_system else 
                3 * A_E / V)

        # Set volume flow coefficient to standard value = 0.07,
        # wich equals shielding coefficient per DIN EN ISO 13789 
        e = .07 

        # Check for exhaust air system with air transfer devices if no heat recovery
        b_exhaust_air_ventilation_system = b_air_transfer_device = \
            b_ventilation_system and tr["heatRecoveryRate"] == 0 
        
        # Apply factor for air transfer devices per Equations 63 or 64
        f_ATD = min(16, (n50 - 1.5) / n50) if b_air_transfer_device else 1 

        # Set coefficient for wind exposure to standard value for moderate shielding
        f = 15  

        # Distinguish between exhaust and heat recovery system (simplification)
        n_sup = 0 if b_exhaust_air_ventilation_system else 1  

        # Use normalized value to differentiate between full balance and imbalance (simplification)
        n_eta = 1

        # Calculate factor for increased/decreased infiltration by mechanical system (eq. 67)
        f_e = 1 / (1 + f / e * ((n_eta - n_sup) / (n50 * f_ATD))**2)  

        # Assume 24 h/day operation in model (assumption)
        t_v_mech = 24  

        # Equation 62: compute infiltration rate with mechanical ventilation
        n_inf = n50 * e * f_ATD * (1 + (f_e - 1) * t_v_mech / 24)  

        # Set volumetric heat capacity of air to 0.34 Wh/(m³·K)
        c_p_aXrho_a = .34

        # Calculate heat transfer coefficient for infiltration per section 6.3.1
        H_V_inf = n_inf * V * c_p_aXrho_a  

        # Equation C.13
        dQ_V_inf__source = H_V_inf * delta_theta_source 

        # Calculate heat transfer coefficient for window ventilation
        # with assumed air change n_win = 0.1/h (assumption) 
        H_V_win = 0.1 * V * c_p_aXrho_a  
        dQ_V_win__source = H_V_win * delta_theta_source  # Equation C.15

        # Sum total ventilation heat gains if θi,c,max,d < θe,max,
        # per Equation C.13 and C.15
        dQ_V__source = dQ_V_inf__source + dQ_V_win__source 

        #-------------------------------------------------------
        # Calculate internal heat gain
        #-------------------------------------------------------

        # Use the sum of internal gains from internal gains file 
        # to represent internal gains (simplification)
        dQ_I_source = load_internalGain_data(tr).resample("1d").mean().max().item()  

        #-------------------------------------------------------
        # Calculate total heat gain
        #-------------------------------------------------------

        # Compute total heat gains on the design day inside the building 
        # zone (power value) per Equation C.3
        dQ_source_max = dQ_S + dQ_T__source + dQ_V__source + dQ_I_source

        #-------------------------------------------------------
        # Calculate temperature difference for heat sink calculations
        #-------------------------------------------------------
        delta_theta_sink = max(0, theta_i - theta_e_max)

        #-------------------------------------------------------
        # Calculate transmission heat flow out of the building
        #-------------------------------------------------------

        # Calculate heat transmission to the outside, Equation C.5
        dQ_T_e__sink = H_T_D * delta_theta_sink  

        # Calculate ground heat flow using static ground temperature 
        # and cooling setpoint temperature in the model (simplification);  
        # according to the standard: dQ_T_s = H_T_s * delta_theta_sink, Equation C.7 
        dQ_T_s__sink = max(0, theta_i - (tr["TGro.k"] - 273.15)) * \
            tr["thermalZone.AFloor"] * tr["UFloor"]  

        # Assume no adjacent zones, so set dQ_T_j to 0 (assumption);  
        # other transmission heat flows: dQ_T_j = H_T_j * max(0, theta_i - theta_j),  
        # Equation C.10
        dQ_T_j = 0  

        # Calculate the sum of transmission heat sinks when θi,c,max,d > θe,max, 
        # according to Equations C.5, C.7, and C.10
        dQ_T__sink = dQ_T_e__sink + dQ_T_s__sink + dQ_T_j 

        #-------------------------------------------------------
        # Calculate ventilation heat flow out of the building
        #-------------------------------------------------------

        # Heat flow due to infiltration, Equation C.12
        dQ_V_inf__sink = H_V_win * delta_theta_sink  

        # Heat flow due to window ventilation, Equation C.14
        dQ_V_win__sink = H_V_inf * delta_theta_sink  

        # Calculate the sum of ventilation heat sinks when θi,c,max,d > θe,max, 
        # according to Equations C.12 and C.14
        dQ_V__sink = dQ_V_inf__sink + dQ_V_win__sink  

        #-------------------------------------------------------
        # Calculate internal heat sink
        #-------------------------------------------------------

        # Assume no internal heat sinks; Q_I_sink is the 
        # sum of internal heat sinks according to Equation C.24 (assumption)
        dQ_I_sink = 0  

        #-------------------------------------------------------
        # Calculate total heat sinks
        #-------------------------------------------------------

        # Calculate total heat sinks according to Equation C.4
        dQ_sink_max = dQ_T__sink + dQ_V__sink + dQ_I_sink  

        #-------------------------------------------------------
        # Calculate time constant of the building
        #-------------------------------------------------------

        # Apply temperature correction factor for calculating the time constant:
        # 1 for direct transmission to outside (external components) and 
        # transmission through ground (component F) according to DIN EN ISO 13370
        Fx_in2out = 1  

        # Use correction factor 0.5 for all other components
        Fx_in2in = 0.5  

        # Apply thermal bridge supplement without detailed building information; 
        # assume ΔUWB = 0.10 W/(m²·K). (For external components with internal 
        # insulation and integrated solid ceilings, assume ΔUWB = 0.15 W/(m²·K)) (assumption)
        delta_U_WB = 0.1  

        # Calculate the area of each component that bounds the building zone to outside 
        # air, unheated or uncooled zones, or the ground. For windows and 
        # doors, use the clear internal structural opening dimensions
        sum_A_j = sum(AExt_list) + sum(AWin_list) + \
            tr["thermalZone.ARoof"] + tr["thermalZone.AFloor"]  
        
        # Calculate the heat transfer coefficient for 2D thermal bridges
        H_T_WB = sum_A_j * delta_U_WB  

        # Set the heat transfer coefficient between heated and 
        # unheated or cooled and uncooled zones to 0 according 
        # to Equation 50 or DIN EN ISO 13789 (equivalent to H_D) (assumption)
        H_T_iu = 0  

        # Calculate the heat transfer coefficient between the 
        # zone and the neighboring zone using the U-value and area 
        # of internal walls according to Equation 53 or 
        # DIN EN ISO 13789 (equivalent to H_D) (simplification)
        H_T_iz = tr["UInt"] * tr["thermalZone.AInt"] 

        # Calculate the heat transfer coefficient through the ground 
        # from floor area and U-value of the floor, analogous to H_T_D 
        # in section 6.2.1 (H_T,s corresponds to G according to 
        # DIN EN ISO 13370) (simplification)
        H_T_s_simplified = tr["thermalZone.AFloor"] * tr["UFloor"]  

        # Calculate the sum of the heat transfer coefficients j for all components 
        # in the thermal envelope of the building zone, to be included in the balance 
        # according to section 6.2
        sumH_T_j = H_T_D * Fx_in2out + H_T_WB * Fx_in2out + H_T_iu * \
            Fx_in2in + H_T_iz * Fx_in2in + H_T_s_simplified * Fx_in2out

        #%%sumH_V_k: Sum of ventilation heat transfer coefficients
        # Calculate the sum of all ventilation heat transfer coefficients 
        # for airflows entering with outdoor temperature
        sumH_V_k = H_V_inf + H_V_win  

        #%%H_V_mech_theta: Mechanical ventilation
        # Use total air change rate as supply rate if supply and exhaust air system is present; 
        # otherwise, set supply air change rate to zero if only exhaust air ventilation or 
        # no ventilation system is installed (assumption). Airflow during system operation 
        # follows Equations 92 to 93.
        n_mech_sup = 0 if b_exhaust_air_ventilation_system or not \
            (b_ventilation_system) else tr["airChangeRate"]  

        # Calculate daily average air change rate through mechanical ventilation 
        # according to Equation 90
        n_mech = n_mech_sup * t_v_mech / 24  

        # Calculate ventilation heat transfer coefficient of mechanical ventilation
        # (see section 6.3.3)
        H_V_mech = n_mech * V * c_p_aXrho_a  

        # Simplification from standard assuming HVAC without cooling 
        # function: For HVAC systems without cooling and residential 
        # ventilation systems, the uncorrected heat transfer coefficient 
        # of the system airflow is used in Equation 135. (simplification)
        # Thus: H_V_mech_theta = H_V_mech; Set temperature-weighted heat transfer 
        # coefficient of mechanical ventilation, according to 
        # Equations 136 to 138
        H_V_mech_theta = H_V_mech  

        # Calculate total heat transfer coefficient of the building zone
        # from transmission and ventilation heat transfer 
        # coefficients according to section 5.5.2
        H = sumH_T_j + sumH_V_k + H_V_mech_theta  

        # Calculate time constant of the building zone according to 
        # section 6.7.2, but without mechanical ventilation
        tau = C_wirk / H  

        #-------------------------------------------------------
        # Calculate cooling demand
        #-------------------------------------------------------
        #%% dQ_c_max: Cooling load
        # Approximate calculation of required maximum cooling 
        # capacity according to Equation C.1
        dQ_c_max = 0.8 * (dQ_source_max - dQ_sink_max) * (1 + 0.3 * 
            np.exp(-tau / 120)) - C_wirk / 60 * (delta_theta - 2) + \
                C_wirk / 40 * (12 / t_c_op_d - 1)  
        
        tr["coolingPower"] = dQ_c_max.item()

        return tr
        