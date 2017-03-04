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
        self.__normdata = {"all_encounter_data" : None,
                           "all_person_data" : None}
        for name in table_names:
            self.__data[name] = pd.read_pickle(filepath + name + '.pickle')

    def __getitem__(self,name):
        if self.__normdata.has_key(name):
            if self.__normdata.get(name) is None:
                if name == "all_encounter_data": self.create_enc_table()
                if name == "all_person_data": self.create_person_table()
            return self.__normdata[name]
        
        return self.__data.__getitem__(name)
        
    def get_underlying(self):
        return self.__data
    
    def create_enc_table(self):
        # Helper function to convert string values to floats
        # 87 Glucose column have BP values which this function ignores and assigns NaN
        # TODO: Swap the erroneous column values. Filter out outliers
        NaN = float("NaN")
        def to_float(x):
            try:
                return float(x)
            except ValueError:
                return NaN
                
        # Split up the BP field into Systolic and Diastolic readings
        d_enc = self.__data["all_encounter_data"]
        pattern = re.compile("(?P<BP_Systolic>\d+)\s*\/\s*(?P<BP_Diastolic>\d+)")
        d_enc = pd.merge(d_enc, d_enc["BP"].str.extract(pattern, expand=True),
                         left_index=True, right_index=True)
        
        # Drop columns with multiple values for a single Enc_ID (and drop Enc_ID, Person_ID)
        # When multiple values are observed, take the mean and merge them back into the complete table
        self.__normdata["all_encounter_data"] = \
            pd.merge(d_enc.drop(["A1C",
                                 "BMI",
                                 "BP",
                                 "BP_Systolic",
                                 "BP_Diastolic",
                                 "Glucose",
                                 "Enc_ID",
                                 "Person_ID"], axis=1).drop_duplicates().set_index("Enc_Nbr"),
                     d_enc.loc[:,["Enc_Nbr",
                                  "A1C",
                                  "BMI",
                                  "Glucose",
                                  "BP_Systolic",
                                  "BP_Diastolic"]].groupby("Enc_Nbr").agg(lambda x: np.mean(x.map(to_float))),
                     left_index=True, right_index=True)
        
        # Add diagnoses to table
        dEI = self.__data["ICD_for_Enc"].loc[:,["Enc_Nbr", "Diagnosis_Code_ID"]]
        
        # Manually fix erroneous values
        dEI.loc[90899]="367.4"
        dEI.loc[168442]="362.3"
        
        # Diabetes is under 250.* and 362.0.* for ICD9 and E08,E09,E10,E11,E13 for ICD10
        dEI["DM"]=dEI["Diagnosis_Code_ID"].str.contains("^250.*|^362\.0.*|^E(?:0[89]|1[013])(?:\.[A-Z0-9]{1,4})?")

        # Macular edema is under 362.07 for ICD9 and E(08|09|10|11|13).3([1-5]1|7) for ICD10
        dEI["ME"]=dEI["Diagnosis_Code_ID"].str.contains("^362\.07|^E(?:0[89]|1[013])\.3(?:[1-5]1|7).*")

        # Mild Nonproliferative Diabetic Retinopathy is under 362.04 for ICD9 and E(08|09|10|11|13).32
        dEI["mNPDR"]=dEI["Diagnosis_Code_ID"].str.contains("^362\.04|^E(?:0[89]|1[013])\.32.*")

        # Moderate Nonproliferative Diabetic Retinopathy is under 362.05 for ICD9 and E(08|09|10|11|13).33
        dEI["MNPDR"]=dEI["Diagnosis_Code_ID"].str.contains("^362\.05|^E(?:0[89]|1[013])\.33.*")

        # Severe Nonproliferative Diabetic Retinopathy is under 362.06 for ICD9 and E(08|09|10|11|13).34
        dEI["SNPDR"]=dEI["Diagnosis_Code_ID"].str.contains("^362\.06|^E(?:0[89]|1[013])\.34.*")

        # Proliferative Diabetic Retinopathy is under 362.02 for ICD9 and E(08|09|10|11|13).35
        dEI["PDR"]=dEI["Diagnosis_Code_ID"].str.contains("^362\.02|^E(?:0[89]|1[013])\.35.*")
        
        # Diabetic Retinopathy
        dEI["DR"]=dEI["mNPDR"] & dEI["MNPDR"] & dEI["SNPDR"] & dEI["PDR"]
        
        # Glaucoma Suspect is under 365.0 for ICD9 and H40.0 for ICD10
        dEI["Glaucoma_Suspect"]=dEI["Diagnosis_Code_ID"].str.contains("^365\.0.*|^H40\.0.*")
        
        # Open-angle Glaucoma is under 365.1 for ICD9 and H40.1 for ICD10
        dEI["Open-angle_Glaucoma"]=dEI["Diagnosis_Code_ID"].str.contains("^365\.1.*|^H40\.1.*")
        
        # Cataract is under 366 for ICD9 and H25 and H26 for ICD10
        dEI["Cataract"]=dEI["Diagnosis_Code_ID"].str.contains("^366(?:\.\d{1,2})?|^H2[56](?:\.[A-Z0-9]{1,4})?")
        
        self.__normdata["all_encounter_data"] = \
            pd.merge(self.__normdata["all_encounter_data"],
                     dEI.drop(["Diagnosis_Code_ID"],axis=1).groupby("Enc_Nbr").any(),
                     left_index=True, right_index=True)
                     
    def create_person_table(self):
        d_enc = self["all_encounter_data"]
        
        # Average the past year of data
        f = lambda x: x[x["Enc_Date"]>=x["Enc_Date"].max() - pd.DateOffset(years=1)].drop(["Person_Nbr","Enc_Date"],axis=1).mean()
        columns = ["Enc_Date", "Person_Nbr", "A1C", "BMI", "Glucose", "BP_Systolic", "BP_Diastolic"]
        self.__normdata["all_person_data"] = \
            pd.merge(self.__data["demographics"].set_index("Person_Nbr"),
                     d_enc.loc[:,columns].groupby("Person_Nbr").apply(f),
                     left_index=True, right_index=True)

        # Combine all diagnoses
        columns = ["Person_Nbr","DM","DR","ME","MNPDR","PDR","SNPDR","mNPDR",
                   "Glaucoma_Suspect","Open-angle_Glaucoma","Cataract"]
        self.__normdata["all_person_data"] = \
            pd.merge(self.__normdata["all_person_data"],
                     d_enc.loc[:,columns].groupby("Person_Nbr").any(),
                     left_index=True, right_index=True)
