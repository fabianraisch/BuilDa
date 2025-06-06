import os
import shutil
from fmpy import read_model_description, extract
from fmpy.fmi2 import FMU2Slave
import pandas as pd
import json
import platform

class FMUWrapper:
    def __init__(self,
                 fmu_path: os.path,
                 start_time
                 ):
                
        self.fmu_path = fmu_path
        self.model_description = read_model_description(self.fmu_path)
        self.vrs = dict()

        # Get the parameter data from the FMU
        for variable in self.model_description.modelVariables:
            self.vrs[variable.name]={"type":variable.type,"reference":variable.valueReference,"start":variable.start}

        #get start values from model description
        self.fmu_default_dict={k:
            float(self.vrs[k]["start"]) if self.vrs[k]["type"]=="Real" 
                and self.vrs[k]["start"]!=None else \
            str(self.vrs[k]["start"]) if self.vrs[k]["type"]=="String" 
                and self.vrs[k]["start"]!=None else \
            int(self.vrs[k]["start"]) if self.vrs[k]["type"]=="Integer" 
                and self.vrs[k]["start"]!=None  else \
            bool(self.vrs[k]["start"]) if self.vrs[k]["type"]=="Boolean" 
                and self.vrs[k]["start"]!=None  else \
            self.vrs[k]["start"] \
            for k in self.vrs.keys()}

        ##store start values to a json file (only use, if all start values are available!)
        #json.dump(self.fmu_default_dict, open("resources/FMUs/fmu_state_dict.json","w"), indent=4, sort_keys=True)

        #fill missing start values with those from json
        self.fmu_default_dict.update({k:v for k,v in \
            json.load(open("resources/FMUs/fmu_state_dict.json","r")).items() \
            if k in self.fmu_default_dict.keys() and self.fmu_default_dict[k]==None})
        

        self.time = start_time

        self.init_FMU()


    def test_fmu_parameterizing(self, parameters:dict,b_verbose_mode=False) -> int:
        '''
        Test if parameters were properly written to the FMU.

        This function verifies if the parameters defined in the provided dictionary
        match the values currently set in the FMU.
        Takes into account possible minor differences between float numbers in main 
        program and FMU because of precision limits, etc.
        Additionally the attributes of the involved parameters are read out from the 
        FMU and verified to be appropriate for manipulation.

        Args:
            parameters (dict): A dictionary containing parameter name:value pairs to verify on the FMU.
            b_verbose_mode (bool, optional): If set to True, the function will print messages also
                                            indicating successful parameter configurations. Defaults to False.

        Returns:
            int: The number of errors found during the parameter verification process.
        '''
        error_threshold=1e-9
        
        fmu_variables=read_model_description(self.fmu_path).modelVariables #Extract the FMU variables and attributes from the FMU file to verify if the attributes of a specific variable are appropriate for setting values.

        n_errors=0
        fmu_state_dict=self.get_fmu_state_dict(parameters.keys())
        for k in parameters.keys():
            fmu_value=fmu_state_dict[k]
            if type(parameters[k]) in [float,int,bool]:
                b_properly_written=abs(parameters[k]-fmu_value) < error_threshold
            elif type(parameters[k]) in [str]:
                if isinstance(fmu_value,bytes): fmu_value=fmu_value.decode()
                b_properly_written=parameters[k]==fmu_value
            else: print("##not handled datatype ",type(parameters[k]),"parameter",k,"cannot be testet.")
            if not(b_properly_written):
                print("##WARNING - MISMATCH: tried to set",k,"to",parameters[k],"actual value",fmu_value)
                n_errors+=1
            else:
                #check if fmu parameter attributes are appropriate for values to be set after fmu compilation
                fmu_variable=[v for v in fmu_variables if v.name==k][0]
                causality=fmu_variable.__getattribute__("causality")
                variability=fmu_variable.__getattribute__("variability")
                if causality!="parameter" and (variability=="tunable" or variability=="fixed"):
                    print("##WARNING - INAPROPRIATE ATRIBUTE CAUSALITY: tried to set",k,"to",parameters[k],"actual value is "+str(fmu_value)+", but causality is","\""+causality+"\"","and variability is","\""+variability+"\".","The set parameter value probably wouldn't be used in simulation")
                    n_errors+=1
                else:
                    if b_verbose_mode:
                        print("#SUCCESSFULLY SET PARAMETER: tried to set",k,"to",parameters[k],"value is now",fmu_value,"parameter attributes(causality:variability):",causality+":"+variability)
        return n_errors

    def init_FMU(self):
        '''
        Instantiates and initializes the FMU object.

        This method creates an instance of the FMU2Slave using the model's GUID and other parameters, then instantiates the FMU and sets up the experiment starting from the current time.

        '''        
        self.fmu = FMU2Slave(
            guid=self.model_description.guid,
            unzipDirectory=self.__get_unzip_dir(),
            modelIdentifier=self.model_description.coSimulation.modelIdentifier,
            instanceName='fmu_variations'
        )
        self.fmu.instantiate()
        self.fmu.setupExperiment(startTime=self.time)


    def step_FMU(self, step_size):
        '''
        Executes a simulation step for the FMU.

        Parameters:
        - step_size (float): The size of the time step.

        Updates the current time after executing the FMU's step.
        '''
        self.fmu.doStep(
            currentCommunicationPoint=self.time,
            communicationStepSize=step_size
        )
        self.time += step_size

    def  __get_unzip_dir(self):

        ''' Private function to get the directory the fmu writes files.

        Arguments: none.

        Returns:
            the directory the fmu writes in.
        '''

        return extract(self.fmu_path)

    def terminate_fmu(self):

        ''' Function to terminate the FMU and free the space.

        Arguments: none.

        Returns: none.
        '''
        try:
            self.fmu.terminate()
            if platform.system().lower()=="linux": #currently deactivated on windows as it broke the execution in tests
                self.fmu.freeInstance() 
            shutil.rmtree(self.fmu.unzipDirectory)
        except Exception as e:
            print("FMU could not be terminated properly. Maybe no simulation was done after init step.")

    def save_state_fmu(self):
        '''
        Gets the current state of the FMU in serialized form, stores it in a class variable and returns it.

        This method retrieves the FMU state using `getFMUstate()` and then serializes it with `serializeFMUstate()`. The serialized state is returned for later use.
        '''
        self.state = self.fmu.getFMUstate()
        self.bstate = self.fmu.serializeFMUstate(state=self.state)
        return self.bstate

    def set_state_fmu(self):
        '''
        Sets a previously stored FMU state to the FMU.

        This method deserializes the stored state using `deSerializeFMUstate()` and sets it to the FMU with `setFMUstate()`. Raises a ValueError if no state has been loaded.

        '''       
        if self.bstate is None:
            raise ValueError("No state loaded. Call load_state_fmu() first.")
        
        self.state = self.fmu.deSerializeFMUstate(self.bstate)
        self.fmu.setFMUstate(self.state)

    def reset_fmu(self):
        '''
        Resets the FMU to its initial state.
        '''        
        self.fmu.reset()

    def alter_in_fmu(self, param_dict):
        '''
        Helper function to alter a set of parameters in the FMU given in a dict.

        Args:
            - params: Dict with the parameter to change as key and the corresponding changed value.

        Returns: None
        '''

        for variable, value in param_dict.items():
            if self.vrs[variable]["type"]=="Real":
                self.fmu.setReal([self.vrs[variable]["reference"]],[value])
            elif self.vrs[variable]["type"]=="String":
                self.fmu.setString([self.vrs[variable]["reference"]],[value])
            elif self.vrs[variable]["type"]=="Boolean":
                self.fmu.setBoolean([self.vrs[variable]["reference"]],[value])
            elif self.vrs[variable]["type"]=="Integer":
                self.fmu.setInteger([self.vrs[variable]["reference"]],[value])
            else:
                print("unknown type "+ self.vrs[variable]["type"],"for variable",variable)
    
    
    def get_fmu_state_dict(self, variables_to_read):
        '''
        Helper function to read parameters of the FMU and return it with the respective values in a dict.

        Args: 
            - variables_to_read: The variables that need to be read from the FMU.
                    if variables_to_read=="all" read out all fmu variables

        Returns: Dict with the current FMU state (minimal).
        '''
        
        state_dict = dict()
        if type(variables_to_read) is str and variables_to_read.lower()=="all".lower(): 
            variables_to_read=self.vrs.keys()
        for variable in variables_to_read:
            try:
                if self.vrs[variable]["type"]=="Real":
                    value=self.fmu.getReal([self.vrs[variable]["reference"]])[0]
                elif self.vrs[variable]["type"]=="String":
                    value=self.fmu.getString([self.vrs[variable]["reference"]])[0]
                elif self.vrs[variable]["type"]=="Boolean":
                    value=self.fmu.getBoolean([self.vrs[variable]["reference"]])[0]
                elif self.vrs[variable]["type"]=="Integer":
                    value=self.fmu.getInteger([self.vrs[variable]["reference"]])[0]
                elif self.vrs[variable]["type"]=="Enumeration": #apparently can be read out as float
                    value=self.fmu.getReal([self.vrs[variable]["reference"]])[0] #enumeration-variable readout
                else:
                    print("unknown type "+ self.vrs[variable]["type"],"for variable",variable)
                    continue
                state_dict[variable]=value
            except(KeyError): #triggers when a variable should be read out that doesn't exist in the fmu's parameter set
                print("##ignoring variable",variable,"as it isn't in the fmu parameter set")
                continue
        return state_dict

    def save_current_fmu_variables(self,file_name:str=None):
        '''
        Save all FMU variables to a file for debugging.

        Args:
            file_name (str): Optional filename; if None, a default name will be generated.

        Returns:
            str: The filename.
        '''
        fmu_state_dict=self.get_fmu_state_dict(variables_to_read="all")

        if not(file_name): file_name="current_fmu_state.csv"
        df=pd.DataFrame(data={"value at t="+str(self.time):fmu_state_dict.values()},index=fmu_state_dict.keys()).sort_index(axis=0)

        pd.concat([df],axis=1).to_csv(file_name,sep=",")
        return file_name

