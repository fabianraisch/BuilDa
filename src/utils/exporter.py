import os
import pandas as pd
import numpy as np
import shutil
import datetime
import re

class Exporter():

    def __init__(self,
                 fmu_path,
                 config_path,
                 output_path
                 ):
        
        '''
        Initializes the exporter.

        Args:
            - fmu_path: The path containing the fmu that was used in this simulation.
            - output_path: The path outputs will be loaded into.

        Returns: None
        '''
        self.fmu_path = fmu_path
        self.fmu_name = os.path.split(self.fmu_path)[-1]
        self.config_path=config_path
        self.config_name=os.path.split(config_path)[-1]
        self.output_path = output_path
        self.b_short_output_folder_name=True

        self.ts_csv_prefix = "_"

        self.dir_name = self.__create_dir_name()
        self.__check_dir()						


    def __create_dir_name(self):

        ''' Static function to create an output directory incorporating the current time.

		Arguments: none.

		Returns:
			a name string based on the current timestamp.
		'''

        name_prefix = self.fmu_name+"__"+self.config_name
        name_suffix = str(datetime.datetime.now())[:19]
        name_suffix = name_suffix.replace(" ", "_")
        name_suffix = name_suffix.replace("-", "")
        name_suffix = name_suffix.replace(":", "")
        if self.b_short_output_folder_name:
            return f"{name_suffix}"
        else:
            return f"{name_prefix}_{name_suffix}"
    

    def export_csv(
			self, 
			rows, 
			header,
            header_time_columns,
            info,
			param_input_list,
			var_param
		):

        ''' Export a csv file to a new dir in the output directory

		Arguments:
			arr: 				the array containing rows to export into the csv file.
			header:				a list containing the header of the csv file.
			variations:		    variations for creating the variations info text file. 
			info:				dict containing all variables with their respective values.

		Returns:
			the newly created directory the csv file is written into.

		The export csv function first creates a new dir inside the output
		directory for this csv file only. After that, this function creates
		a new csv file and writes the rows specified in the arr argument.
		'''

		#convert param_input_list and var_param to DataFrames
        vars_start=pd.DataFrame(param_input_list,columns=["name","value"]).set_index("name").sort_index(axis=0)
        variated_param=pd.DataFrame(var_param,columns=["name"]).set_index("name").sort_index(axis=0)

		# Deduce denomination for results of variation by using list of varied parameters
        # by creating a string that clearly identifies a simulation in the simulation series
        identstr="_"
        #iterate only through variated parameters
        for param in np.sort(np.unique(variated_param.index.values)):
            val=vars_start.loc[param].value
            #shorten suffix, if parameter is file path, only use prefix of file name
            if type(val) is str and ("fileNam" in param or "fileName" in param): 
                val='.'.join(os.path.basename(val).split('.')[:-1])   #filename without suffix
            #if parameter is component's RC-Distribution, shorten parameter values (lists) by rouding, removing brackets
            elif type(val) is list and "distribution" in param:
                val=re.sub(r"[\[\] ]","",str([round(e/sum(val),2) for e in val]))
            #shorten every element of the parameter name to 3 symbols
            param="_".join([w[:3] for w in param.split("_")])
            #extend identstr by adapted name of parameter in pascal case and value
            identstr+="#"+self.__to_pascal_case(param)+"_"+str(val)

		# Create a new directory to save the csv file in.
        dirname_prefix = identstr
        if identstr=="_":
            dirname_prefix += "single"
        save_dir = self.__make_csv_save_dir(dirname_prefix)
        file_name=os.path.join(save_dir,os.path.basename(save_dir)+".csv")

		# Save the csv file generated from the given array.
        rows = self.__transform_timestamps(rows,time_columns=header_time_columns) 
        header = header_time_columns + header[1:] # Replace the first column named "timestamp" with the new columns
        df = pd.DataFrame(rows,columns=header)

         #sort the columns, except the time_columns specified in "header_time_columns", that are placed on the beginning
        df=df[header_time_columns + sorted(set(df.columns)-set(header_time_columns)) ]

        df.to_csv(file_name)

		# Add csv file containing all info of the vars set.
        pd.DataFrame(param_input_list).to_csv(os.path.join(save_dir,"vars_start.csv"),header=["config_var","value"],index=False)

		# Add parm.txt config to the save directory.
        pd.DataFrame(info).to_csv(os.path.join(save_dir,"para_to_fmu.csv"),header=["config_var","value"],index=False)

		# Add csv file containg only the variated param for the specific simulation
        pd.DataFrame(var_param).to_csv(os.path.join(save_dir,"variated_param.csv"),header=["fmu_var"]*(len(var_param)>0),index=False)

        return self.dir_name
    

    def __make_csv_save_dir(self, dirname):

        ''' 
        Function to make a custom directory to write the csv files.
        If the path already exists, da current datetime is added.
        If directory name is too long for the operating system, it's shortened.
        
        Arguments: 
            dirname: name of the directory to be created.
        
        Returns:
        - path to the newly created directory.
        - the name of the newly created directory.
        '''
        dirname_length_margin=5
        #get the OS limit for path names, set to 260 (usually windows), if os.pathconf doen't exist
        max_path_length=os.pathconf('.', 'PC_NAME_MAX') if hasattr(os,"pathconf") else 260  
        while True:    #find an output path, that doesn't yet exist and whose folder length doesn't exceed the OS limit
            path_to_save = os.path.join(self.__get_dir_path(), dirname)
            if os.path.exists(path_to_save):
                print("#output folder name '"+path_to_save+"' already exists - adding timestamp")
                dirname+="__duplicate"+datetime.datetime.now().isoformat().replace(":","-") #add timestamp if directory already exists
            else:
                #check if the path name exceeds the OS limit and shorten it if necessary
                if len(dirname) > max_path_length:  
                    print("#Ouptut folder name too long - will be shortened...")  
                    n_chars2cut=len(os.path.basename(dirname)) - os.pathconf('.', 'PC_NAME_MAX')
                    dirname_splitted=dirname.split("__duplicate")
                    dirname_splitted[0]=dirname_splitted[0][:-n_chars2cut-3-dirname_length_margin]+"..."
                    dirname="__duplicate".join(dirname_splitted)
                else:
                    break

        os.makedirs(path_to_save)
        return path_to_save
    

    def __check_dir(self):

        ''' 
        Checks if the designated directory already exists. If not, the directory will be created.

		Arguments: none.

		Returns: none.

		'''

        to_check = self.__get_dir_path()
		
        if not os.path.exists(to_check):
            print("\ncreating directory:\n",to_check,"\n")
            os.makedirs(to_check)

    
    def __get_dir_path(self):

        ''' 
        Create the new directory.

		Arguments: none.

		Returns:
			the current directory path.
		'''

        return os.path.join(self.output_path, self.dir_name)
    

    def __to_pascal_case(self,snake_str):
		
        ''' 
        Convert a snake_case string to a PascalCase string.

		Arguments:
			snake_str: the snake_case string to convert.

		Returns:
			the PascalCase string.
		'''
        components = snake_str.split('_')

        return ''.join(x.title() for x in components)
    

    def __transform_timestamps(self,data,time_columns):
        '''
        Transform the first column of each sublist to new columns as stated in parameter time_columns:
		     e.g. "time:second_of_day": second of the day and "time:day_of_year": day of the year.

		Args:
			data (list of lists): Input data with each sublist containing a timestep in seconds.
            time_columns (list of strings): Columns to be created based on the time stamp in seconds in the data (1st column).

		Returns:
			list of lists: Transformed data with new columns replacing the original timestep column.
		'''
        time_expressions_available_functions_dict = {
            "second": lambda current_time: (current_time - start_time).total_seconds(),
            "minute": lambda current_time: (current_time - start_time).total_seconds()//60,
            "hour": lambda current_time: (current_time - start_time).total_seconds()//3600,
            "day": lambda current_time: (current_time - start_time).total_seconds()//86400,
            "year": lambda current_time: (current_time - start_time).total_seconds()//31536000,
            "second_of_day": lambda current_time: current_time.hour * 3600 + current_time.minute * 60 + current_time.second,
            "minute_of_day": lambda current_time: current_time.hour * 60 + current_time.minute,
            "day_of_year": lambda current_time: current_time.timetuple().tm_yday,
            "day_of_month": lambda current_time: current_time.day,
            "week_of_year": lambda current_time: current_time.isocalendar()[1],
            "nanosecond_of_month": lambda current_time: (current_time - current_time.replace(day=1)).total_seconds() * 1e9
        }

		# Assume the input time in seconds is elapsed time since the start of the first day
        start_time = datetime.datetime(2023, 1, 1)  # An arbitrary starting point (start of a non leap year) to make datetime calculations and exctract seconds of day and day of year afterwards (--> assuming here, it's January 1st, 2023 0 a.m.)

        for index_row,row in enumerate(data):
            second = row[0]    #total time in seconds (elapsed simulation time)
            current_time = start_time + datetime.timedelta(seconds=second)

            
            time_expression_list=[time_expressions_available_functions_dict[v](current_time) for v in time_columns]

			# Add the new columns and retain column with original time stamp
            data[index_row]=time_expression_list + row[1:]


        return data


    def copy_fmu_and_config(self):

        ''' 
        Function to copy the FMU file given in the path argument to the output directory.

		Arguments:
			fmu_path: the path where the fmu file will be copied from.

		Returns: none
		'''

        dst_path = self.__get_dir_path()

        shutil.copy(self.fmu_path, dst_path)
        shutil.copy(self.config_path, dst_path)

    def save_actual_git_commit_to_dir(self):
        ''' 
        Function to save information about the actual commit of the git repository (where HEAD was pointing during the simulation series) into the simulation destination directory
            
        Arguments:
                None

        Returns: none
        '''
        gitdir=".git"
        c=0
        while not(os.path.exists(gitdir)):
            gitdir=os.path.join("..",gitdir)
            if c>999: break #avoid infinite loop if there is no git repository
            c+=1
        if c<=999:
            actual_commit_str=open(os.path.join(gitdir,"logs","HEAD"),"r").read().split("\n")[-2:][0]
            dst_path=os.path.join(self.__get_dir_path(),"git_log_actual_commit.txt")
            open(dst_path,"w").write(actual_commit_str)

