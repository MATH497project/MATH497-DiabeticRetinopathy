import numpy as np
import pandas as pd
import re

class Data:

    def __init__(self, filepath):
        table_names = {'all_encounter_data': 'all_encounter_data.pickle',
                       'demographics': 'demographics_Dan_20170304.pickle',
                       'encounters': 'encounters.pickle',
                       'ICD_for_Enc': 'ICD_for_Enc_Dan_20170304.pickle',
                       'SNOMED_problem_list': 'SNOMED_problem_list.pickle',
                       'refractive_index': '2017_03_30_refractive_index_columns.pickle',
                       'visual_accuity': '2017_03_30_visual_acuity_columns.pickle',
                       'family_hist': 'pgp1.csv'}
        self.__data = {}
        self.__normdata = {"all_encounter_data" : None,
                           "all_person_data" : None}
        for name, file_name in table_names.items():
            if name == 'family_hist':
                self.__data[name] = pd.read_csv(filepath + file_name)
            else:
                self.__data[name] = pd.read_pickle(filepath + file_name)

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

        # Add the processed refractive indices and visual accuity numerical as quantitive data
        d_enc = d_enc.merge(
                self.__data['refractive_index'][['MR_OD_SPH_Numeric', 'MR_OD_CYL_Numeric',
                                                'MR_OS_SPH_Numeric', 'MR_OS_CYL_Numeric']],
                left_on = 'Enc_Nbr', right_index = True)

        d_enc = d_enc.merge(
                self.__data['visual_accuity'][['MR_OS_DVA_ability', 'MR_OD_DVA_ability',
                                               'MR_OS_NVA_ability', 'MR_OD_NVA_ability']],
                left_on = 'Enc_Nbr', right_index = True)

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
        quantitive_columns=['A1C', 'BMI', 'Glucose', 'BP_Diastolic', 'BP_Systolic',
                            'MR_OD_SPH_Numeric', 'MR_OD_CYL_Numeric',
                            'MR_OS_SPH_Numeric', 'MR_OS_CYL_Numeric',
                            'MR_OS_DVA_ability', 'MR_OD_DVA_ability',
                            'MR_OS_NVA_ability', 'MR_OD_NVA_ability']
        for column in quantitive_columns:
            temp0 = pd.to_numeric(d_enc[column], errors='coerce')
            temp = temp0[temp0.notnull()]
            Q2 = temp.quantile(0.75)
            Q1 = temp.quantile(0.25)
            IQR = Q2-Q1
            d_enc[column] = temp0.map(lambda x: x if Q1 - 1.5 * IQR < x < Q2 + 1.5 * IQR else NaN)

        # Drop columns with multiple values for a single Enc_Nbr
        # When multiple values are observed, take the mean and merge them back into the complete table
        # columns = list(filter_outliers)
        self.__normdata["all_encounter_data"] = \
            pd.merge(d_enc.drop(quantitive_columns, axis=1).drop_duplicates().set_index("Enc_Nbr"),
                     d_enc.groupby("Enc_Nbr")[quantitive_columns].mean(),
                     left_index=True, right_index=True)

        # Add diagnoses to table
        dEI = self.__data["ICD_for_Enc"].loc[:,["Enc_Nbr", "Diagnosis_Code_ID"]]

        # Manually fix erroneous values
        # dEI.loc[90899]="367.4"
        # dEI.loc[168442]="362.3"

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
        d_enc = self["all_encounter_data"].copy()

        # Average the past year of data
        def average_func(column):
            recent = column[column["Enc_Date"]>=column["Enc_Date"].max() - pd.DateOffset(years=1)]
            return recent.drop(["Person_Nbr","Enc_Date"],axis=1).mean()

        columns1 = ["Person_Nbr","DOB","Gender","Race"]
        columns2 = ["Enc_Date", "Person_Nbr", "A1C", "BMI", "Glucose", "BP_Systolic", "BP_Diastolic",
                    'MR_OD_SPH_Numeric', 'MR_OD_CYL_Numeric',
                    'MR_OS_SPH_Numeric', 'MR_OS_CYL_Numeric',
                    'MR_OS_DVA_ability', 'MR_OD_DVA_ability',
                    'MR_OS_NVA_ability', 'MR_OD_NVA_ability']
        self.__normdata["all_person_data"] = \
            pd.merge(self.__data["demographics"].loc[:,columns1].set_index("Person_Nbr"),
                     d_enc.loc[:,columns2].groupby("Person_Nbr").apply(average_func),
                     left_index=True, right_index=True)

        # Collect most recent encounter date
        self.__normdata["all_person_data"]["Last_Encounter"] = \
            d_enc.groupby("Person_Nbr")["Enc_Date"].max()

        # Add the recent smoking status to each person
        def recent_smoking(groupbyblock):
            tempblock = groupbyblock[groupbyblock['Smoking_Status'].notnull()]
            templist = tempblock.sort_values(['Enc_Date'],ascending=False)['Smoking_Status'].str.lower().values
            if len(templist)==0:
                return 'unknown if ever smoked'
            else:
                return templist[0]
        self.__normdata["all_person_data"]['recent_smoking_status'] = \
            d_enc.groupby('Person_Nbr').apply(lambda x: recent_smoking(x))

        # Merge the processed family history (DM and Glucose, the 2 most frequent
        # diagnoses in parent and grandparent level)
        fami = self.__data['family_hist'].set_index('Person_Nbr')[['DM', 'G']]
        family_DM_converter_dict = {1:'P_DM', 2:'P_NDM', 3:'Gp_DM', 4:'Gp_NDM',
                                    5:'Gp_SM_P_DM', 6: 'G_DM_P_NDM', 7:'G_NDM_P_DM',
                                    8:'GP_NDM_P_NDM', 9:'Unknown' }
        family_G_converter_dict = {1:'P_G', 2:'P_NG', 3:'Gp_G', 4:'Gp_NG',
                                   5:'Gp_G_P_G', 6: 'GP_G_P_NG', 7: 'G_NG_P_G',
                                   8: 'GP_NG_P_NG',  9: 'Unknown'}
        fami['family_DM'] = fami['DM'].map(lambda x: family_DM_converter_dict[x])
        fami['family_G'] = fami['G'].map(lambda x: family_G_converter_dict[x])
        self.__normdata["all_person_data"] = \
            self.__normdata["all_person_data"].merge(fami[['family_DM', 'family_G']],
            left_index = True, right_index = True)

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
            'American Indian or Alaska Native':'Other',
            'American Indian/Alaskan Native':'Other',
            'American Indian':'Other',
            'Native American Indian':'Other',
            'Alaskan Native':'Other',
            'Asian':'Asian',
            'Chinese':'Asian',
            'Indian':'Asian',
            'Caucasian':'White',
            'White (Not Hispanic / Latino)':'White',
            'White':'White',
            'Declined to specify':'Other',
            'Unknown/Not Reported':'Other',
            'Greek':'White',
            'Native Hawaiian or Other Pacific Islander':'Other',
            'Hawaiian':'Other',
            'Other Pacific Islander (Not Hawaiian)':'Other',
            'Hispanic Or Latino (All Races)':'Hispanic or Latino',
            'Hispanic':'Hispanic or Latino',
            'More than one race':'Other',
            'Multiracial':'Other',
            'Multi-racial':'Other','Moroccan':'White',
            float('nan'):'Other',
            'Other Race':'Other',
            'Other Race (Jamaican)':'Other'
        }
        self.__normdata["all_person_data"]['Race'] = \
            self.__normdata["all_person_data"]['Race'].apply(lambda x: standard_race_conversion_dict.get(x,"Other"))

        # Add Age at most recent encounter
        self.__normdata["all_person_data"]["Age"] = \
            self.__normdata["all_person_data"]["Last_Encounter"].map(lambda x: x.year)\
                - self.__normdata["all_person_data"]["DOB"].map(lambda x: x.year)
