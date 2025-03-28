from src.converter_functions.converter_function import ConverterFunction
import pandas as pd 


class Component_properties_calculator(ConverterFunction):
    '''
    Calculate: the R- and C-Value distributions for the RC-Elements in the components (e.g. wall, floor, roof, internal wall)
    Based on: number of RC-Elements, overall U-Value and heat capacitance of the components, zone dimensions
    '''
    def __init__(self):
        super().__init__()

    @staticmethod
    def calc_distribution(self,value,n,distribution=None):
        """
        Distributes a given value into n parts based on a specified distribution list.

        Args:
            value (float): The total value to be distributed.
            n (int): The number of parts to distribute the value into.
            distribution (list of floats, optional): A list of fractions representing the distribution. 
                If None, the value will be distributed equally among all parts.
                If the sum of the distribution is not equal to 1, the values will be normalized.

        Returns:
            list of floats: The distributed values as a list, where each element of the list corresponds to a part.
        """
        if distribution==None:
                print("WARNING: calc_distribution: no distribution given for value",value)
                print("\t==> assuming homogeneous distribution")
                distribution=[1/n for c in range(n)]
        if len(distribution)<n:
                raise ValueError("distribution has too few elements, there should be "+str(n)+" but distribution has "+str(len(distribution))+": '"+str(distribution)+"'")
        if len(distribution)>n:
                raise ValueError("distribution has too much elements, there should be "+str(n)+" but distribution has "+str(len(distribution))+": '"+str(distribution)+"'")
        if sum(distribution)!=1: 
                #print(f"Sum of elements in in distribution {distribution} !=1-> scaling values to correct distribution")
                correction_factor=1/sum(distribution)
                distribution=[distribution[i]*correction_factor for i in range(len(distribution))]
        value_distributed=[value*distribution[i] for i in range(len(distribution))]
        return(value_distributed)
    
    @staticmethod
    def calc_R_conductive(self,U,Rsi,Rse,A):
        """
        calculate the conductive resistance of the entire component from U-Value by subtracting the heat transfer resistances Rsi (interior) and Rse (exterior) and dividing through the area
        Args:
            U-value:  U-value of component
            Rsi    :  interior heat transfer resistor of component
            Rse    :  exterior heat transfer resistor of component
            A      :  Area of component
        returns:
            R_cond   : conductive heat resistor of component
        """
        R_cond=((1/U)-Rsi-Rse)/A
        return(R_cond)


    def convert(self, variable_dict):
        tr = variable_dict
        # The wall consists of n R-C-elements + one RRem
        # the total R-value and the total C-Value of the component(exterior wall, floor, roof, interior wall+ceiling) is divided according to the distribution parameter between the RC-Elements
        #%%external wall
        tr.update(
            dict(zip(
                    ["thermalZone.RExt["+str(c)+"]" for c in range(1,tr["thermalZone.nExt"]+1)]+["thermalZone.RExt"+"Rem"],
                    self.calc_distribution(self,
                        value=self.calc_R_conductive(self,U=tr["UExt"],  Rsi=tr["Rsi_extWall"],  Rse=tr["Rse_extWall"],  A=tr["wallExt_area_total"]),
                        n=tr["thermalZone.nExt"]+1,
                        distribution=tr["extWall_R_distribution"]
                    )
                )
            )
        )
        tr.update(
            dict(
                zip(
                    ["thermalZone.CExt["+str(c)+"]" for c in range(1,tr["thermalZone.nExt"]+1)],
                    self.calc_distribution(self,
                        value=tr["heatCapacity_wall"]*tr["wallExt_area_total"],
                        n=tr["thermalZone.nExt"],
                        distribution=tr["extWall_C_distribution"]
                    )
                )
            )
        )

        #%%floor
        tr.update(
            dict(zip(
                    ["thermalZone.RFloor["+str(c)+"]" for c in range(1,tr["thermalZone.nFloor"]+1)]+["thermalZone.RFloor"+"Rem"],
                    self.calc_distribution(self,
                        value=self.calc_R_conductive(self,U=tr["UFloor"],Rsi=tr["Rsi_floor"],Rse=0,A=tr["thermalZone.AFloor"]),
                        n=tr["thermalZone.nFloor"]+1,
                        distribution=tr["floor_R_distribution"]
                     )
                )
            )
        )
        tr.update(
            dict(
                zip(
                    ["thermalZone.CFloor["+str(c)+"]" for c in range(1,tr["thermalZone.nFloor"]+1)],
                    self.calc_distribution(self,
                        value=tr["heatCapacity_floor"]*tr["thermalZone.AFloor"],
                        n=tr["thermalZone.nFloor"],
                        distribution=tr["floor_C_distribution"]
                    )  
                )
            )
        )
        #%%roof
        tr.update(
            dict(zip(
                    ["thermalZone.RRoof["+str(c)+"]" for c in range(1,tr["thermalZone.nRoof"]+1)]+["thermalZone.RRoof"+"Rem"],
                    self.calc_distribution(self,
                        value=self.calc_R_conductive(self,U=tr["URoof"],Rsi=tr["Rsi_roof"],Rse=tr["Rse_roof"],A=tr["thermalZone.ARoof"]),
                        n=tr["thermalZone.nRoof"]+1,
                        distribution=tr["roof_R_distribution"]
                    )
                )
            )
        )
        tr.update(
            dict(
                zip(
                    ["thermalZone.CRoof["+str(c)+"]" for c in range(1,tr["thermalZone.nRoof"]+1)],
                    self.calc_distribution(self,
                        value=tr["heatCapacity_roof"]*tr["thermalZone.ARoof"],
                        n=tr["thermalZone.nRoof"],
                        distribution=tr["roof_C_distribution"]
                    ) 
                )
            )
        )
        #%%internal wall
        tr.update(
            dict(zip(
                    ["thermalZone.RInt["+str(c)+"]" for c in range(1,tr["thermalZone.nInt"]+1)],
                    self.calc_distribution(self,
                        value=self.calc_R_conductive(self,U=tr["UInt"] * 2,  Rsi=tr["Rsi_intWall"],  Rse=0,  A=tr["thermalZone.AInt"] + (tr["n_floors"]-1) * tr["thermalZone.AFloor"] * 2),  #Simplified, thickness of the wall already specified by resistance, no transition Rse on one side because it's only half of the wall, modeling the intermediate ceilings as internal walls.
                        n=tr["thermalZone.nInt"],
                        distribution=tr["intWall_R_distribution"]
                    )
                )
            )
        )
        heat_capacity_furniture=tr["zone_length"]*tr["zone_width"]*tr["heatCapacity_furniture_per_m2"]*tr["n_floors"] #J/(K*m²)*m²
        tr.update(
            dict(
                zip(
                    ["thermalZone.CInt["+str(c)+"]" for c in range(1,tr["thermalZone.nInt"]+1)],
                    self.calc_distribution(self,
                        value=tr["heatCapacity_internalWall"] * tr["thermalZone.AInt"] + (tr["n_floors"]-1)*tr["thermalZone.AFloor"] * tr["heatCapacity_floor"] + heat_capacity_furniture,    #simplified, thickness of the wall already determined by capacity + capacity of the intermediate floors.
                        n=tr["thermalZone.nInt"],
                        distribution=tr["intWall_C_distribution"]
                    )
                )
            )
        )
        #%%window
        tr["thermalZone.RWin"]=self.calc_R_conductive(self,U=tr["UWin"],Rsi=tr["Rsi_window"],Rse=tr["Rse_window"],A=tr["win_area_total"])

        return tr



