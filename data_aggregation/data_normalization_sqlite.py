import pandas as pd
from pprint import pprint
import json
import numpy as np
import dataset


# ICD_list table must be re-built from, presumably, ICD_for_Enc due to some entries being
# pre-18th birthday.  ICD_list entries are not timestamped!
table_names = ['all_encounter_data', 'demographics', 'encounters', 'family_hist_for_Enc',
               'family_hist_list', 'ICD_for_Enc',
               # 'ICD_list',
               'macula_findings_for_Enc',
               'SL_Lens_for_Enc', 'SNOMED_problem_list', 'systemic_disease_for_Enc', 'systemic_disease_list']

person_data = ['demographics','family_hist_list', 'systemic_disease_list', 'SNOMED_problem_list']

encounter_data = ['all_encounter_data', 'encounters', 'family_hist_for_Enc', 'ICD_for_Enc', 'macula_findings_for_Enc',
                   'SL_Lens_for_Enc', 'systemic_disease_for_Enc']



path = 'E:\\anil\\IIT Sop\\Term02\\MATH497\\ICO_data\\original_pickle\\'

# read tables into dataframes
dfs = [pd.read_pickle(path + name + '.pickle') for name in table_names]

for df in dfs:
    if df is not None:
        df.columns = [col.decode("utf-8-sig") for col in df.columns]

dfs = [df.where((pd.notnull(df)), None) for df in dfs if df is not None]

sqlite_file = 'dr_data_sqlite.db'
db = dataset.connect('sqlite:///'+sqlite_file)



for df_index, df in enumerate(dfs):
    db.begin()
    print table_names[df_index], len(df)
    table = db[table_names[df_index]]
    df_columns =  set(df.columns.values)
    enc_key = 'Enc_Nbr'
    person_key = 'Person_Nbr'
    row_count = 0
    for i, dfrow in df.iterrows():
        rowdict = dict(dfrow)
        for k, v in rowdict.iteritems():
            if isinstance(v, pd.tslib.Timestamp):
                rowdict[k] = v.toordinal()


        try:
            table.insert(rowdict)
        except:
            for k, v in rowdict.iteritems():
                try:
                    rowdict[k]=rowdict[k].decode("utf-8-sig")
                except:
                    pass
            try:
                table.insert(rowdict)
            except:
                print rowdict



        row_count+=1
        if row_count%10000==0:
            print 'rows inserted :', row_count


    db.commit()