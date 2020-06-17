''' add alerts data from coverity'''
import common, sql
import datetime
import json
import os
import time
import dateutil.parser
import sys
import pandas as pd
import numpy as np
import logging

def get_alert_type_id(type, impact, category):
    selectQ='''select id from alert_type
            where type=%s and impact=%s and category=%s '''
    results=sql.execute(selectQ,(type, impact, category)) 
    if not results:
        insertQ='insert into alert_type values(null,%s,%s,%s)';
        sql.execute(insertQ,(type, impact, category))
        results=sql.execute(selectQ,(type, impact, category))
    return results[0]['id']

def get_file_id(filename, projectId):
    selectQ='select id from file where filepath_on_coverity =%s and project_id=%s '
    results=sql.execute(selectQ,(filename, projectId))
    if not results:
        insertQ='insert into file values(null,%s,%s,null)'
        sql.execute(insertQ,(projectId, filename))
        results=sql.execute(selectQ,(filename, projectId))
    return results[0]['id']

def process_alerts(datalist, projectId):
    '''
    takes datalist, process it as per db, and returns the dataframe
    '''
    df=pd.DataFrame(datalist)
    df.insert(0,'id',[np.NaN]*len(df))
    df.insert(2,'project_id',[projectId]*len(df))
    df=common.replace_blankString_with_NaN(df)
    
    df['type']=df.apply(lambda row: get_alert_type_id(row.type, row.impact,row.category),axis=1)
    df['file']=df.apply(lambda row: get_file_id(row.file, row.project_id),axis=1)
    df['firstDetected']=df.apply(lambda row: sql.convert_datetime_to_sql_format(row.firstDetected),axis=1)
    
    df['is_invalid']=[np.NaN]*len(df)
    drop=['impact','category','comparison','FirstSnapshotDate',
            'FirstSnapshotDescription', 'FirstSnapshotStream',
            'FirstSnapshotTarget', 'FirstSnapshotVersion', 'fixTarget',
            'lastDetected', 'lastDetectedDescription', 'lastDetectedStream',
            'lastDetectedTarget', 'lastDetectedVersion','MISRARigor'
        ]    
    df=df.drop(drop, axis=1)

    column_names_in_db=sql.get_table_columns('alert')
    df.columns=column_names_in_db

    return df

def separate_exiting_and_new_alerts(datalist, projectId):
    #turn into oldest to newest 
    datalist.reverse()

    q="select distinct cid from alert where project_id=%s order by cid desc"
    results = sql.execute(q,(projectId,))
    cidsInDb= {}  #implement a hashmap for efficient lookup
    for item in results:
        cidsInDb[item['cid']]=1

    existingAlerts=[]
    newAlerts=[]

    for data in datalist:
        if int(data['cid']) in cidsInDb:
            existingAlerts.append(data)
        else:
            newAlerts.append(data)
    
    return existingAlerts, newAlerts
    
def add_new_alerts(datalist, projectId):
    before=common.get_alert_count(projectId)

    if not datalist:
        return
    df=process_alerts(datalist, projectId)
    sql.load_df('alert',df)

    after=common.get_alert_count(projectId)
    logging.info("%s new alerts added", after-before)

def get_alert_id(cid, projectId):
    q='select id from alert where cid=%s and project_id=%s'
    results=sql.execute(q,(cid,projectId))
    if not results:
        return np.nan
    else:
        return results[0]['id']

def update_existing_alerts(datalist, projectId):
    if not datalist:
        return
    df=process_alerts(datalist, projectId)
    
    df= df.drop('id', axis=1)
    df['id']=df.apply(lambda row: get_alert_id(row.cid, row.project_id), axis=1)
    update=['status','owner','classification','action','ext_ref','last_snapshot_id',
            'last_triaged','merge_extra','merge_key','owner_name']
    affected_rows = sql.update_df('alert',df, update)

    logging.info("%s rows updated",affected_rows)

def add_n_update_alerts(projectId, datafile):
    datalist=common.read_xml_file_to_list_of_dicts(datafile)
    
    existingAlerts, newAlerts= separate_exiting_and_new_alerts(datalist, projectId)
    logging.info('existing alerts: %s, new alerts:%s',len(existingAlerts),len(newAlerts))

    add_new_alerts(newAlerts, projectId)
    update_existing_alerts(existingAlerts, projectId)

if __name__=="__main__":
    #read system arguments
    project_name=sys.argv[1]
    datafile=sys.argv[2]
    projectId=common.get_project_id(project_name)
    
    

        
        


        
