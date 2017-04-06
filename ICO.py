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
        # Swap the erroneous column values.
        d_enc = self.__data["all_encounter_data"].drop(["Enc_ID","Person_ID"], axis=1)

        pattern0= re.compile("\d+\s*\/\s*\d+")
        index1 = d_enc['Glucose'].str.contains(pattern0, na=False)
        temp = d_enc.loc[index1, 'Glucose']
        d_enc.loc[index1, 'Glucose'] = d_enc.loc[index1, 'BP']
        d_enc.loc[index1, 'BP'] = temp

        index2 = d_enc.BP[d_enc.BP.notnull()][~d_enc.BP[d_enc.BP.notnull()].str.contains('/')].index
        temp = d_enc.loc[index2, 'Glucose']
        d_enc.loc[index2, 'Glucose'] = d_enc.loc[index2, 'BP']
        d_enc.loc[index2, 'BP'] = temp

        # Split up the BP field into Systolic and Diastolic readings
        pattern1 = re.compile("(?P<BP_Systolic>\d+)\s*\/\s*(?P<BP_Diastolic>\d+)")
        d_enc = pd.merge(d_enc, d_enc["BP"].str.extract(pattern1, expand=True),
                         left_index=True, right_index=True).drop("BP", axis=1)

        # Define ranges for reasonable values. Identify the data outside of 1.5 times of IQR as outliers
        NaN = float("NaN")
        # filter_outliers = {
        #     "A1C" : lambda x: x if 3.89 < x < 30 else NaN,
        #     "BMI" : lambda x: x if 10 < x < 300 else NaN,
        #     "BP_Systolic" : lambda x: x if 60 < x < 251 else NaN,
        #     "BP_Diastolic" : lambda x: x if 30 < x < 180 else NaN,
        #     "Glucose" : lambda x: x if 20 < x < 800 else NaN
        # }
        # for column in list(filter_outliers):
        #     d_enc[column] = pd.to_numeric(d_enc[column], errors='coerce').map(filter_outliers[column])
        quantitive_columns=['A1C', 'BMI', 'Glucose', 'BP_Diastolic', 'BP_Systolic']
        for column in quantitive_columns:
            temp0 = pd.to_numeric(d_enc[column], errors='coerce')
            temp = temp0[temp0.notnull()]
            Q2 = temp.quantile(0.75)
            Q1 = temp.quantile(0.25)
            IQR = Q2-Q1
            d_enc[column] = temp0.map(lambda x: x if Q1 - 1.5 * IQR < x < Q2 + 1.5 * IQR else NaN)

        # Drop columns with multiple values for a single Enc_Nbr
        # When multiple values are observed, take the mean and merge them back into the complete table
        #columns = list(filter_outliers)
        self.__normdata["all_encounter_data"] = \
            pd.merge(d_enc.drop(quantitive_columns, axis=1).drop_duplicates().set_index("Enc_Nbr"),
                     d_enc.groupby("Enc_Nbr")[quantitive_columns].mean(),
                     left_index=True, right_index=True)

        # Add diagnoses to table
        dEI = self.__data["ICD_for_Enc"].loc[:,["Enc_Nbr", "Diagnosis_Code_ID"]]

        # Manually fix erroneous values
        dEI.loc[90899]="367.4"
        dEI.loc[168442]="362.3"

        diagnoses = {
            # Diabetes is under 250.* and 362.0.* for ICD9 and E08,E09,E10,E11,E13,O24 for ICD10
            "DM" : "^250.*|^362\.0.*|^E(?:0[89]|1[013])(?:\.[A-Z0-9]{1,4})?|^O24.*",
            # Macular edema is under 362.07 for ICD9 and E(08|09|10|11|13).3([1-5]1|7) for ICD10
            "ME" : "^362\.07|^E(?:0[89]|1[013])\.3(?:[1-5]1|7).*",
            # Mild Nonproliferative Diabetic Retinopathy is under 362.04 for ICD9 and E(08|09|10|11|13).32
            # Background/unspecified DR is considered as mNPDR as suggested (362.01 for ICD9, E(08|09|10|11|13).31 for ICD10)
            "mNPDR" : "^362\.0(4|1)|^E(?:0[89]|1[013])\.3(2|1).*",
            # Moderate Nonproliferative Diabetic Retinopathy is under 362.05 for ICD9 and E(08|09|10|11|13).33
            "MNPDR" : "^362\.05|^E(?:0[89]|1[013])\.33.*",
            # Severe Nonproliferative Diabetic Retinopathy is under 362.06 for ICD9 and E(08|09|10|11|13).34
            "SNPDR" : "^362\.06|^E(?:0[89]|1[013])\.34.*",
            # Proliferative Diabetic Retinopathy is under 362.02 for ICD9 and E(08|09|10|11|13).35
            "PDR" : "^362\.02|^E(?:0[89]|1[013])\.35.*",
            # Glaucoma Suspect is under 365.0 for ICD9 and H40.0 for ICD10
            "Glaucoma_Suspect" : "^365\.0.*|^H40\.0.*",
            # Open-angle Glaucoma is under 365.1 for ICD9 and H40.1 for ICD10
            "Open_angle_Glaucoma" : "^365\.1.*|^H40\.1.*",
            # Cataract is under 366 for ICD9 and H25 and H26 for ICD10
            "Cataract" : "^366(?:\.\d{1,2})?|^H2[56](?:\.[A-Z0-9]{1,4})?"
        }
        for diagnosis, pattern in diagnoses.iteritems():
            dEI[diagnosis]=dEI["Diagnosis_Code_ID"].str.contains(pattern)

        self.__normdata["all_encounter_data"] = \
            pd.merge(self.__normdata["all_encounter_data"],
                     dEI.groupby("Enc_Nbr")[list(diagnoses)].any(),
                     left_index=True, right_index=True)

        # Select the worst diagnosis of DR for each multi-diagnosis encounter
        target_diagnosis = ['PDR', 'SNPDR', 'MNPDR', 'mNPDR']
        def worstDR(row):
            temp = np.where(row)[0]
            if len(temp)>0:
                return target_diagnosis[temp[0]]
            else:
                return 'no_DR'

        self.__normdata['all_encounter_data']['DR_diagnosis'] = \
            self.__normdata["all_encounter_data"].apply(lambda x: worstDR(x[target_diagnosis]), axis=1)



    def create_person_table(self):
        d_enc = self["all_encounter_data"]

        # Average the past year of data
        def average_func(column):
            recent = column[column["Enc_Date"]>=column["Enc_Date"].max() - pd.DateOffset(years=1)]
            return recent.drop(["Person_Nbr","Enc_Date"],axis=1).mean()

        columns1 = ["Person_Nbr","DOB","Gender","Race"]
        columns2 = ["Enc_Date", "Person_Nbr", "A1C", "BMI", "Glucose", "BP_Systolic", "BP_Diastolic"]
        self.__normdata["all_person_data"] = \
            pd.merge(self.__data["demographics"].loc[:,columns1].set_index("Person_Nbr"),
                     d_enc.loc[:,columns2].groupby("Person_Nbr").apply(average_func),
                     left_index=True, right_index=True)

        # Collect most recent encounter date
        self.__normdata["all_person_data"]["Last_Encounter"] = \
            d_enc.groupby("Person_Nbr")["Enc_Date"].max()

        # Combine all diagnoses
        columns = ["DM","ME","MNPDR","PDR","SNPDR","mNPDR",
                    "Glaucoma_Suspect", "Open_angle_Glaucoma","Cataract"]
        self.__normdata["all_person_data"] = \
            pd.merge(self.__normdata["all_person_data"],
                     d_enc.groupby("Person_Nbr")[columns].any(),
                     left_index=True, right_index=True)

        # Select the worst DR diagnosis
        target_diagnosis = ['PDR', 'SNPDR', 'MNPDR', 'mNPDR']

        d_enc['DR_diagnosis_idx'] = d_enc['DR_diagnosis'].apply(lambda x: target_diagnosis.index(x) if x!='no_DR' else 4)
        self.__normdata['all_person_data']['worst_DR'] = \
            d_enc.groupby('Person_Nbr')['DR_diagnosis_idx'].min().apply(lambda x: target_diagnosis[x] if x<4 else 'no_DR')

        # Select the recent DR diagnosis
        def recent_DR(groupbyblock):
            templist = groupbyblock.sort_values(['Enc_Date'],ascending=False)['DR_diagnosis_idx'].values
            temp = np.where(templist!=4)[0]
            if len(temp) > 0:
                return target_diagnosis[templist[temp[0]]]
            else:
                return 'no_DR'

        self.__normdata['all_person_data']['recent_DR'] = \
            d_enc.groupby('Person_Nbr').apply(lambda x: recent_DR(x))


        # Standardize Race
        standard_race_conversion_dict = {
            'African American':'Black or African American',
            'Black or African American':'Black or African American',
            'Black/African American (Not Hispanic)':'Black or African American',
            'American Indian or Alaska Native':'Other Race',
            'American Indian/Alaskan Native':'Other Race',
            'American Indian':'Other Race',
            'Native American Indian':'Other Race',
            'Alaskan Native':'Other Race',
            'Asian':'Asian',
            'Chinese':'Asian',
            'Indian':'Asian',
            'Caucasian':'White',
            'White (Not Hispanic / Latino)':'White',
            'White':'White',
            'Declined to specify':'Unknown',
            'Unknown/Not Reported':'Unknown',
            'Greek':'White',
            'Native Hawaiian or Other Pacific Islander':'Other Race',
            'Hawaiian':'Other Race',
            'Other Pacific Islander (Not Hawaiian)':'Other Race',
            'Hispanic Or Latino (All Races)':'Hispanic or Latino',
            'Hispanic':'Hispanic or Latino',
            'More than one race':'Two or More Races',
            'Multiracial':'Two or More Races',
            'Multi-racial':'Two or More Races','Moroccan':'White',
            float('nan'):'Unknown',
            'Other Race':'Other Race',
            'Other Race (Jamaican)':'Other Race'
        }
        self.__normdata["all_person_data"]['Race'] = \
            self.__normdata["all_person_data"]['Race'].apply(lambda x: standard_race_conversion_dict.get(x,"Unknown"))

        # Add Age at most recent encounter
        self.__normdata["all_person_data"]["Age"] = \
            self.__normdata["all_person_data"]["Last_Encounter"].map(lambda x: x.year)\
                - self.__normdata["all_person_data"]["DOB"].map(lambda x: x.year)
