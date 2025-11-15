import requests
import pandas as pd
import numpy as np
import sys

#pip instll requests pandas numpy matplotlib

#<cmd> python mos_generator.py [startyear] [endyear] [latitude(optional)] [longitude(optional)] [output_filename(optional)]

#2005 <= startyear, endyear <= 2020


"""
This script is meant to create an EPW-style .mos file using an old one as referenced
for filling in data that is not needed and thus does not need to be fetched anew.
The reference file should span 1 year and is automatically duplicated to match the
amount of years new data is fetched for.
cols_to_replace are then replaced with the fetched data from the PVGIS data bank
(https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en)
and the .mos file is saved.
"""


#If script is called without arguments/from an IDE, it uses the default.
#Therefore args an be passed through editing default.
default = {
    "startyear": 2005,
    "endyear": 2009,
    "lat": "48.1371",                   #need to be calculated from map or can be easily retrieved by location, eg. through https://www.renewables.ninja/
    "lon": "11.5754",                   #(48.1371, 11.5754) corresponds to Munich
    "raddatabase": "PVGIS-SARAH3",      #for europe, alternatively use PVGIS-ERA5 for worldwide data
    "out_filename": None,               #creates a filename from lat-lon-number_of_years.mos iff None, else uses provided filename     
    "plot": False                       #for automatic plotting afterwards, not implemented yet
    }

cols_to_replace = {
    "C2": "Temp",
    "C9": "HGloHor",
    "C10": "HDirNor",
    "C11": "HDifHor"
    }

folder = "weatherFiles/" #the subfolder the weatherfiles are stored in
reference_file = "weatherFiles/Munich.mos" #name of reference file to take file structure and irrelevant data from. Should span exactly 1 year.

if default["plot"]:
    import matplotlib.pyplot as plt

def fetch_pvgis_data(startyear, endyear, lat, lon, raddatabase):

    print(f"Fetching weather data from {raddatabase} from {startyear} to {endyear} at (lat: {lat}, lon: {lon})")

    # Define parameters for the request
    params = {
        "lat": lat,
        "lon": lon,
        "outputformat": "json",
        "usehorizon": 1,  # Use horizon limit (terrain is taken into account for solar radiance)
        "raddatabase": raddatabase, 
        "startyear": startyear,
        "endyear": endyear,
        "components": 1
    }

    # PVGIS API URL for hourly time series
    url = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"

    # Request data from PVGIS
    response = requests.get(url, params=params)


    # Check for errors
    if response.status_code != 200:
        print(f"HTTP Error: {response.status_code} - {response.text}")
        exit()

    # Parse JSON response
    data = response.json()
    timeseries = data["outputs"]["hourly"]


    # Convert to DataFrame
    df = pd.DataFrame(timeseries)

    #ghi = dhi + dni*cos(azimuth) where dhi=Gd(i), dni = Gb(i) and azimuth = 90deg-elevation where H_sun=elevation
    #as described in https://en.wikipedia.org/wiki/Solar_irradiance

    ghi = np.array(df["Gd(i)"]) + np.array(df["Gb(i)"])*np.cos((90-np.array(df["H_sun"]))*2*np.pi/360)
    out = np.array([df["T2m"], df["Gd(i)"], df["Gb(i)"], ghi])
    return pd.DataFrame(out.T, columns = ["Temp", "HDifHor", "HDirNor", "HGloHor"])

def read_mos(filename):

    print(f"Reading reference file {filename}")
    with open(filename, "r") as f:
        data = f.read()

    # scans for header and data and splits it
    n_cols = int(data[data.find(",")+1: data.find(")")])  #start of header contains "*double tab1(rows,cols)\n*"
    last_header_line = data.find(f"C{n_cols}")
    header_end = data[last_header_line:].find("\n")+last_header_line
    header = data[:header_end+1] 
    dat = data[header_end+1:]

    #converts the data to a numpy array
    arr1 = dat.split("\n")[:-1]
    arr2 = np.array([i.split("\t")[:-1] for i in arr1])
    #print(arr2.shape)
    header_shape = (int(header[header.find("(")+1:header.find(",")]), int(header[header.find(",")+1:header.find(")")]))
    if arr2.shape != header_shape:
        print(f"ERROR while reading .mos file: list dimensions {arr2.shape} do not match header {header_shape}!")
        exit()
    df = pd.DataFrame(arr2, columns = [f"C{i+1}" for i in range(n_cols)])
    return df, header

def replace_cols_and_save_mos(startyear,
                              endyear,
                              lat=default["lat"],
                              lon=default["lon"],
                              raddatabase=default["raddatabase"],
                              mos_filename=reference_file,
                              out_filename=default["out_filename"],
                              plot = default["plot"],
                              subfolder = folder):

    #some args checking
    startyear = int(startyear)
    endyear = int(endyear)
    n_years = 1+endyear-startyear
    if out_filename is None:
        out_filename = lat + "-" + lon + f"-{n_years}years.mos"
    elif out_filename.find(".mos") == -1:
        out_filename = out_filename + ".mos"

    #reads the base .mos file
    base, header = read_mos(mos_filename)

    #duplicates it n_years times and creates continuous time column
    out = pd.concat([base for _ in range(n_years)], ignore_index=True, sort=False)
    out["C1"] = np.linspace(0, len(out["C1"])-1, len(out["C1"]))*3600 #1 row/hour -> 3600s/row

    #fetches pvgis data
    data = fetch_pvgis_data(startyear, endyear, lat, lon, raddatabase)
    
    #replaces reference .mos values
    for key in cols_to_replace:
        out[key] = data[cols_to_replace[key]]

    #adjust length value in .mos header
    header = (f"{header[:header.find("(")+1]}"
                    f"{str(len(out["C1"]))}"
                    f"{header[header.find(","):header.find("#COMMENTS 1,")]}"
                    f"#COMMENTS 1, data {list(cols_to_replace)} taken from https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en. "
                    "All other data is taken from a different reference file and thus not reliable. "
                    "Header information is not reliable but might structurally be necessary for modelica and is thus not modified.\n"
                    "#COMMENTS 2, -\n"
                    f"{header[header.find("#DATA"):]}")

    #stores file and copies header from reference file
    with open(subfolder + out_filename, "w", newline = "") as f:
        f.write(header)
        out.to_csv(f, sep = "\t", header = False, index = False)
    print(f"Data saved to {subfolder + out_filename}")
    return subfolder + out_filename

if __name__ == "__main__":
    if len(sys.argv) == 3:
        replace_cols_and_save_mos(sys.argv[1], sys.argv[2])

    elif len(sys.argv) == 4:
        replace_cols_and_save_mos(sys.argv[1], sys.argv[2], out_filename=sys.argv[3])

    elif len(sys.argv) == 5:
        replace_cols_and_save_mos(sys.argv[1], sys.argv[2], lat = sys.argv[3], lon = sys.argv[4])

    elif len(sys.argv) == 6:
        replace_cols_and_save_mos(sys.argv[1], sys.argv[2], lat = sys.argv[3], lon = sys.argv[4], out_filename = sys.argv[5])
    elif len(sys.argv) == 1: #if script is called without args/from IDE
        replace_cols_and_save_mos(default["startyear"], default["endyear"])










