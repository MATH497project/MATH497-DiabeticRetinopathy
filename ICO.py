import numpy as np
import pandas as pd
import re

class Data:
    def __init__(self, filepath):
        table_names = ['all_encounter_data', 'demographics', 'encounters',
                       'family_hist_for_Enc', 'family_hist_list',
                       'ICD_for_Enc', 'macula_findings_for_Enc',
                       'SL_Lens_for_Enc', 'SNOMED_problem_list', 
                       'systemic_disease_for_Enc', 'systemic_disease_list']
        self.__data = {}
        self.__normdata = {"all_encounter_data" : None}
        for name in table_names:
            self.__data[name] = pd.read_pickle(filepath + name + '.pickle')

    def __getitem__(self,name):
                self.create_enc_table()
        if self.__normdata.has_key(name):
            if self.__normdata.get(name) is None:
            return self.__normdata[name]
        
        return self.__data.__getitem__(name)
        
    def get_underlying(self):
        return self.__data
    
    def create_enc_table(self):
        # Helper function to convert string values to floats
        # 87 Glucose column have BP values which this function ignores and assigns NaN
        def func(x):
            try:
                return float(x)
            except ValueError:
                return float("NaN")
                
        # Split up the BP field into Systolic and Diastolic readings
        d_enc = self.__data["all_encounter_data"]
        pattern = re.compile("(\d+)\s*\/\s*(\d+)")
        temp = d_enc["BP"].str.extract(pattern, expand=True)
        d_enc["BP_Systolic"] = temp[0]
        d_enc["BP_Diastolic"] = temp[1]
        temp = None
        
        # Drop columns with multiple values for a single Enc_ID (and drop Enc_Nbr)
        temp = d_enc.drop(["A1C",
                           "BMI",
                           "BP",
                           "BP_Systolic",
                           "BP_Diastolic",
                           "Glucose",
                           "Enc_Nbr"], axis=1).drop_duplicates().set_index("Enc_ID", verify_integrity=True)

        # When multiple values are observed, take the mean and merge them back into the complete table
        self.__normdata["all_encounter_data"] =\
            temp.merge(d_enc.loc[:,["Enc_ID",
                                    "A1C",
                                    "BMI",
                                    "Glucose",
                                    "BP_Systolic",
                                    "BP_Diastolic"]].groupby("Enc_ID").agg(lambda x: np.mean(x.map(func))),
                       how='outer', left_index=True, right_index=True)
        