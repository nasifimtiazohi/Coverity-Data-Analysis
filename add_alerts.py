''' add alerts data from coverity'''
import common, sql
import datetime
import requests
import json
import os
import time
import dateutil.parser
import sys
import pandas as pd
import numpy as np


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


def separate_exiting_and_new_alerts(datalist, projectId):
    #turn into oldest to newest 
    datalist.reverse()

    q="select distinct cid from alert where project_id=%s order by cid desc"
    results = sql.execute(q,(projectId,))
    lastCID=results[0]['cid']
    for i,data in enumerate(datalist):
        if int(data['cid']) > lastCID:
            break
    
    existing=datalist[:i]
    newAlerts=datalist[i:]

    return existing, newAlerts

def add_new_alerts(datalist, projectId):
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

    sql.load_df('alert',df)

if __name__=="__main__":
    #read system arguments
    project_name=sys.argv[1]
    datafile=sys.argv[2]
    projectId=common.get_project_id(project_name)
    datalist=common.read_xml_file_to_list_of_dicts(datafile)
    
    existing, newAlerts= separate_exiting_and_new_alerts(datalist, projectId)
    print("exisiting alerts: ",len(existing)," new alerts: ",len(newAlerts))

    add_new_alerts(newAlerts, projectId)
    

        # #replace blank data with null
        # for k in data.keys():
        #     if data[k]=="":
        #         data[k]="null"
        
        # #handle bug_type
        # if typeId_ifexists(data["type"])==None:
        #     addBugType(data["type"],data["impact"],data["category"])
        # bugTypeId=typeId_ifexists(data["type"])

        # #handle file
        # if fileId_ifexists(data["file"])==None:
        #     addFile(data["file"])
        # fileId=fileId_ifexists(data["file"])

        
        
        # #add alerts
        # arguments=[
        #     data["cid"], 
        #     project_name,
        #     str(bugTypeId), 
        #     data["status"] ,
        #     datetime.datetime.strptime(data["firstDetected"],'%m/%d/%y').strftime('%y/%m/%d'),
        #     data["owner"],
        #     data["classification"],
        #     data["severity"],
        #     data["action"],
        #     data["displayComponent"],
        #     str(fileId),
        #     data["function"],
        #     data["checker"],
        #     data["occurrenceCount"],
        #     data["cwe"],
        #     data["externalReference"],
        #     data["FirstSnapshot"],
        #     data["functionMergeName"],
        #     data["issueKind"],
        #     data["Language"],
        #     data["lastDetectedSnapshot"],
        #     data["lastTriaged"],
        #     data["legacy"],
        #     data["mergeExtra"],
        #     data["mergeKey"],
        #     data["ownerName"],
        #     0
        # ]
        # # add an escaping string function. not the best practice. but easiest fix.
        # for a in arguments:
        #     if type(a)==str:
        #         a=connection.escape_string(a)
        # query="insert into alerts values (null,"
        # for idx, arg in enumerate(arguments):

        #     #value cleaning
        #     arg=str(arg) #if not string
        #     arg=arg.strip() #if any whitespace ahead or trailing
        #     #remove illegal character
        #     arg=arg.replace('"',"'")



        #     if is_number(arg) or arg=="null":
        #         query+=arg
        #     else:
        #         query+='"'+arg+'"'
        #     if idx<len(arguments)-1:
        #         query+=","
        # query+=");"
        # with connection.cursor() as cursor:
        #     try:
        #         cursor.execute(query)
        #     except Exception as e:
        #         print(e,query)
        #         errors.write(str(e)+"\n")
        


        
