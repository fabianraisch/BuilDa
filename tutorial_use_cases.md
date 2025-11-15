## Simulate variations of example building

The example single family house that comes with BuilDa is based on tabula buildig DE.N.SFH.08.Gen (see https://webtool.building-typology.eu/).

Open **resources/configurations/config_example_singleFamilyHouse.json** to view the corresponding configuration file. You can see a bunch of entries covering building and simulation parameters in there. To simulate the example building you only need to execute
```
python ./main.py resources/configurations/config_example_singleFamilyHouse.json
```
However, if you want to simulate another building with different occupants in another location, etc., this configuration file provides an excellent starting point to create your own variations.

**Hint:** Take a moment to read the comments in the configuration file, as they often provide valuable insights.


### Add locations to simulate <a id="weather_files"></a>
To represent different locations, different weather files cann be applied as the external thermal influences on the building.

Search for the entry **weaDat.fileName** in the configuration file. Add file paths for available weather files of different locations (e.g. Paris, Prague). The paths can be relative starting from the repository's directory.

```
"weaDat.fileName":["resources/weatherFiles/Munich.mos",
                "resources/weatherFiles/Paris.mos",
                "resources/weatherFiles/Prague.mos"],
```

Paths can also be set as wildcard patterns - e.g.:
```
"resources/weahterFiles/P*.mos"
```
standing for all mos files starting with "P" or even:
```
"resources/weahterFiles/*.mos"
```
standing for all .mos-files in the directory "resources/weahterFiles/".



### Add internal gain profiles to simulate
To represent different occupancies as well as other internal gains (e.g. electrical appliances), profiles representing this internal gains can be configured like the weather files (see section <a href="#weather_files">Add locations to simulate</a>).
The entry in the configuration file is called **internalGain.fileName**.
Some predefined internal gain profiles can be found in the directory **resources/internalGainProfiles/**.

**Important note:** If no internal gains should be simulated, the file **NoActivity.txt** must be set.

### Add window opening profiles to simulate
From time to time, occupants might open the window to allo fresh air to get into their homes - depending mainly on their presence, but e.g. as well on their preference for fresh air.
To represent this different behaviours of window ventilation by the occupants, profiles representing window openings can be configured like the weather files (see section <a href="#weather_files">Add locations to simulate</a>).

The entry in the configuration file is called **hygienicalWindowOpening.fileName**.
Some predefined internal gain profiles can be found in the directory **resources/hygienicalWindowOpeningProfiles/**.

**Important note:** If no internal gains should be simulated, the file **no_opening.txt** must be set.


### Configure zone geometry
Adapt the entries **zone_length**, **zone_width**, **floor_height** and **n_floors** in the section **zone geometry**
 to vary the zone geometry. To get three different zone lengths (extension east to west) and three different numbers of floors, adapt **zone_length** and **n_floors** like e.g.:
```
"zone_length":[5,10,15],
...
"n_floors":[1,2,3],
```
If you like, modify relational factors **fATransToAWindow** (defines the transparent fraction of the window), **fARoofToAFloor** (factor, the roof area exceeds the floor area) and **fAInt** (factor that sets the internal walls' area and the external walls' area into relation).

### Configure opaque building components walls, roof and floor
The opaque building components transmit heat from the building to outside (except internal walls) and vice versa while storing heat inside them at the same time.
#### Confiugre heat transmittance by setting the U-Value {#u-value}
To configure the heat transmitance of this components, edit the entries 

**UExt** (external walls),

**UInt** (internal walls), 
 
**URoof** (roof), 

**UFloor** (floor)

Set values mainly between 0.1: very high thermal insulation and 1.5: very low thermal insulation.
To configure e.g. walls with high, medium and low thermal insulation, you can set:
```
    "UExt":[0.2,0.7,1.3],
```

#### Configure heat capacity {#heat_capacity}
Heat capacities influence the thermal inertia of the building model. The following, area specific, capacities can be set:

**heatCapacity_wall** (external walls)

**heatCapacity_floor** (floor)

**heatCapacity_internalWall** (internal walls)

**heatCapacity_roof** (roof)

**heatCapacity_furniture_per_m2** (furniture, etc.)

Values for heat capacity typically range between 50 and 660 J/(m²K) for external walls, 270 and 500 J/(m²K) for floors, and 35 to 400 J/(m²K) for roofs, depending on the construction type (between heavy or lightweight) of the component.

The heat capacity of internal walls is often related to that of external walls; however, it is important to note that there is no standard method for deriving the heat capacity of internal walls applicable to all use cases. Additionally, differences can exist between internal walls, such as those between load-bearing and non-load-bearing walls. In many cases, the heat capacity of internal walls can be estimated to be between 5% and 100% of that of external walls, though exceptions can exist.

The heat capacity of furniture can also vary significantly. A reference value of 2230 J/(m²K) corresponds to 2e-3 m³ of spruce per m² and is considered an appropriate starting point for most cases.




#### Configure RC-Distribution
The RC-Distributions in the **RC-Element's distribution parameters** section describe the proportions of the thermal resistances (there are 3 for the RC-Elements + 1 remaining) as well as of the thermal capacities for each component (external and internal walls, floor, roof) of the building. As such, proportions  are sub parameters of the the R- and C-distribution are dimensionless and represent the thickness as well as the U-value or the capacity for each element in relation to the overall value of the component.
 The order of the proportions is from the inside to the outside of the building, except on the internal walls, where it is from the inside of the building to the interior of the component. As an example, the RC-Distribution of the external wall can be defined manually as follows (derived from ashrae test case 'heavy'):
```
    "extWall_C_distribution":[0.96, 0.01, 0.03],
    "extWall_R_distribution":[0.05, 0.48, 0.45, 0.02],
```
This example RC-distribution represents a wall with outer insulation and high inner thermal mass. This can be inferred looking on the first (most inner) element of the R- and C-distributions with a relativelly high capacity and a relativally low resistance (e.g. concrete layer) and on the second and third elements with high thermal resistance and low thermal capacity.

While the sum of the proportions should always be 1 in the model, it's not necessary to take care of this in the configuration. Thus, e.g. real resistances of capacities could be configured (if available), while BuilDa takes care of scaling this values internally.

As the R- and C-distribution describe actually the proportion of thickness, thermal resistance or capacity of a component, it's worth noting that they are not indepentendt from each other as well as the configured U-values and heat capacities of the component.
To facilitate the configuration, [predefined RC-Distributions](#predefined-rc-distributions) have been created.

##### Predefined RC-Distributions
To facilitate the configuration, some RC-Distributions have been predefined in BuilDa. They can be configured by setting a string with the distribution's name instead of the list of proportions.
There are e.g. the predefined distributions 'monolythic', 'heavy', 'leightweight' (available for all building components) as well as 'baloonFraming', 'perforatedBrick' and 'gasConcrete' (available only for external walls).

### Configure windows
Windows are transparent building components and as such allow solar radiation to enter the building directly, leading to a significant impact on solar heat gains. The window is defined by window to wall fraction for each geographical direction (**fAWin_south**, **fAWin_west**, **fAWin_north**, **fAWin_east**), the solar heat gain coefficient (**thermalZone.gWin**), and the U-value of the window (**UWin**).
To define windows that form 10 % of the exterior walls' area of the building on every geographical direction, set:
```
    "fAWin_south":[0.1],
    "fAWin_west":[0.1],
    "fAWin_north":[0.1],
    "fAWin_east":[0.1],
```
To define a medium insulated window with a low solar heat gain coefficient, you can set:
```                
    "UWin":[2],             
    "thermalZone.gWin":[0.3], 

```


**Hint:** If you want to do **cartesion product variations** (see [README.md](README.md#variation-of-parameters)) on the window to wall fraction for all geographical directions at a time, it is possible to link to other parameters by writing a string of the parameter name instead of the value like:
```
    "fAWin_south":[0.1],
    "fAWin_west":["fAWin_south"],
    "fAWin_north":["fAWin_south"],
    "fAWin_east":["fAWin_south"],
```

### Configure air exchange
Air exchange can be induced (besides [window ventilation](#add-window-opening-profiles-to-simulate)) by infiltration and mechanical ventilation systems with or without heat recovery. The air exchange through infiltration and mechanical ventilation (if exists) can be configured by setting the parameter **airExchangeRate**.
To configure a ventilation system with heat recovery of 80 %, you can specify e.g.:
```
        "heatRecoveryRate":[0.8],    
        "airChangeRate":[3],  
```

### Configure model's internal heating controller
The internal proportional controller can be activated by setting:
```
        "UseInternalController": [1],  
```
This parameter switches between model internal P-Controller and external custom controller for heating. (**1**: internal controller is used, **0**: external controller is used).
Different setpoints for day (6 a.m. to 10 p.m.) and night (10 p.m. to 6 a.m.) can be set as follows:
```
    "roomTempLowerSetpoint":[18], 
    "roomTempUpperSetpoint":[22],  
```

### Heat sources' thermal properties
The proportion of heat transfer types (radiation or convection) from the heat source (heating system or other internal gains) can be configured. For example, the following setting configures a 100 % convective fraction for the heating system and a 40 % convective fraction for other internal gains. The rest corresponds to the radiative fraction.
```
    "internalGainsConvectiveFraction":[0.4],
    "heatingConvectiveFraction":[1],
```


