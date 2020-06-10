import pymysql
import sys
import numpy as np
import datetime
import re
import subprocess
import shlex
import os
from scipy.stats import mannwhitneyu




#open sql connection 
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='soverityscan_sandbox',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results=cursor.fetchall()
    return results
f=open('temp.txt','w')
projects=['Linux','Firefox','Samba','Kodi','Ovirt-engine']
for project in projects:
    query='''select datediff(s.date,a.first_detected) as diff from actionability ac
            join alerts a 
            on a.idalerts=ac.alert_id
            join snapshots s
            on a.last_snapshot_id=s.idsnapshots
            where ac.actionability = 1
            and a.is_invalid=0
            and a.stream="''' + project + '"'
    results=execute(query)
    temp=[]
    for item in results:
            temp.append(item['diff'])
    actionable_lifespan=round(np.median(temp),1)

    query='''select datediff(s.date,a.first_detected) as diff from actionability ac
            join alerts a 
            on a.idalerts=ac.alert_id
            join snapshots s
            on a.last_snapshot_id=s.idsnapshots
            where ac.actionability = 1
            and a.is_invalid=0
            and a.classification!="Bug"
            and a.stream="''' + project + '"'
    results=execute(query)
    temp=[]
    for item in results:
            temp.append(item['diff'])
    nonbugs=temp

    query='''select datediff(s.date,a.first_detected) as diff from actionability ac
            join alerts a 
            on a.idalerts=ac.alert_id
            join snapshots s
            on a.last_snapshot_id=s.idsnapshots
            where ac.actionability = 1
            and a.is_invalid=0
            and a.classification="Bug"
            and a.stream="''' + project + '"'
    results=execute(query)
    temp=[]
    for item in results:
            temp.append(item['diff'])
    bugs=temp
    bug_lifespan=round(np.median(temp),1)

    print(project,mannwhitneyu(np.array(nonbugs),np.array(bugs)))
    
    query='''select datediff(s.date,a.first_detected) as diff from actionability ac
            join alerts a 
            on a.idalerts=ac.alert_id
            join snapshots s
            on a.last_snapshot_id=s.idsnapshots
            where ac.actionability = 0
            and a.is_invalid=0
            and a.stream="''' + project + '"'
    results=execute(query)
    temp=[]
    for item in results:
            temp.append(item['diff'])
    unactionable_lifespan=round(np.median(temp),1)

    temp=[project,actionable_lifespan,bug_lifespan,unactionable_lifespan]
    f.write('&'.join(str(x) for x in temp)+r'\\'+'\n')