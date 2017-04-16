from connect_to_drive import check_and_update
import numpy as np
import pandas as pd
import re

class Data:
    def __init__(self, filepath=None):
        table_file_name_dict = {'all_encounter_data': 'all_encounter_data_Dan_20170415.pickle',
                        'demographics': 'demographics_Dan_20170304.pickle',
                        'encounters': 'encounters.pickle',
                        'family_hist_for_Enc': 'family_hist_for_Enc.pickle',
                        'family_hist_list': 'family_hist_list.pickle',
                        'ICD_for_Enc': 'ICD_for_Enc_Dan_20170304.pickle',
                        'macula_findings_for_Enc': 'macula_findings_for_Enc.pickle',
                        'SL_Lens_for_Enc': 'SL_Lens_for_Enc.pickle',
                        'SNOMED_problem_list': 'SNOMED_problem_list.pickle',
                        'systemic_disease_for_Enc': 'systemic_disease_for_Enc.pickle',
                        'systemic_disease_list': 'systemic_disease_list.pickle',
                        'all_person_data': 'all_person_data_Dan_20170415.pickle',
                        'person_profile': 'person_profile_df.pickle',
                        'visual_accuity': '2017_03_30_visual_acuity_columns.pickle',
                        'refractive_index': '2017_03_30_refractive_index_columns.pickle',
                        'baseline_missingHandled': 'baseline_missingHandled_Dan_20170406.pickle',
                        'baseline_raw': 'baseline_raw_Dan_20170406.pickle'}

        filepath=check_and_update(table_file_name_dict, filepath)

        self.__data = {}

        for k,v in table_file_name_dict.items():
            self.__data[k] = pd.read_pickle(filepath + v)

    def __getitem__(self,name):
        return self.__data.__getitem__(name)
