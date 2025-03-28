import itertools

class Variator():

    def __init__(self,
                 variations,
                 mode
                 ):
        '''
        Initializes a Variator and generates all desired variations for the simulation series, depending on the config and the chosen variation mode.

        Args:
            - Variations: Dict specifying which variations to use.
            - Mode: The variaton mode. ["cartesian_product", "zip"]
        '''
        self.variations: dict = variations
        self.mode = mode

        self.variation_combinations = self._make_variation_combinations()
  
    def get_variated_config_parameters(self):
        '''Retrieve the configuration parameters that have been varied.

        This method returns a list of parameters from the configuration JSON that 
        have more than one value specified, indicating variations'''
        return [k for k in self.variations.keys() if len(self.variations[k])>1]

    def _make_variation_combinations(self):

        '''
        Helper function to create all variation combinations based on the mode given.

        Args: None
        Returns: 
            - List of variations
        '''

        result = []

        variation_tuples = list()

        for variation in self.variations.keys():
            variation_tuples.append((variation, self.variations[variation]))
                             
        if self.mode in ("cartesian_product") :
            print("Doing cartesian product variations.")
            for subset in itertools.combinations(variation_tuples, len(variation_tuples)):
                if not subset:
                    continue

                list_zipped = list(zip(*subset))
                permutation_products = itertools.product(*list_zipped[1])

                for permutation_product in permutation_products:
                    tmp_list = []
                    for i, p in enumerate(permutation_product):
                        tmp_list.append((list_zipped[0][i], p))

                    result.append(tmp_list)

            return result     

        if self.mode=="zip":

            print("Doing zip variations.")

            #get the number of variations to calculate, according to the greates number of values given for a parameter
            n_variations=max([len(parameter_list[1]) for parameter_list in variation_tuples]) 
            for i in range(n_variations):
                variation=[]
                for parameter_name,values in variation_tuples:
                    ind=min(i,len(values)-1) #if i exceeds the last index of list, use last index 
                    variation.append((parameter_name,values[ind]))
                result.append(variation)

        return result
    
