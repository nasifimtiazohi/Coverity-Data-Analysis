# import statement
import pymysql
import sys
import numpy as np
import datetime
import re
import subprocess
import shlex
import os
from openpyxl import Workbook
import dateutil.parser as dp

# open sql connection
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='soverityscan_sandbox',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()
    return results

f=open('temp.txt','w')
projects=['Linux','Firefox','Samba','Kodi','Ovirt-engine']

for project in projects:
    query="select count(*) as c from alerts where is_invalid=0 and stream='"+project+"';"
    total_alerts=execute(query)[0]['c']
    # need to subtract new alerts that are alive for less the median lifespan of actionable alerts
    
    query='''select count(*) as c from actionability ac
            join alerts a 
            on a.idalerts=ac.alert_id
            where ac.actionability = 1
            and a.is_invalid=0
            and a.stream="''' + project + '"'
    actionable_count=execute(query)[0]['c']
    
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
    
    actionable_lifespan=np.median(temp)

    query='''select count(*) as c
            from alerts 
            where stream="'''+project+'''"
            and status='New'
            and is_invalid=0
            and datediff(
            (select date
            from snapshots
            where stream="'''+project+'''"
            order by idsnapshots desc
            limit 1),
            first_detected
            ) <=''' +str(actionable_lifespan)
    too_new_to_count=execute(query)[0]['c']
    adjusted_total=total_alerts - too_new_to_count
    actionability_rate=round(((float(actionable_count)/adjusted_total)*100),1)

    query="select count(*) as c from alerts where is_invalid=0 and status='Fixed' and stream='"+project+"';"
    eliminated=execute(query)[0]['c']
    elim_rate=round(((float(eliminated)/total_alerts)*100),1)

    query="select count(*) as c from alerts where is_invalid=0 and classification='Bug' and stream='"+project+"';"
    bug=execute(query)[0]['c']
    bug_rate=round(((float(bug)/total_alerts)*100),1)

    elim=str(eliminated)+' ('+str(elim_rate)+'\%)'
    act=str(actionable_count)+' ('+str(actionability_rate)+'\%)'
    traiged_bug=str(bug)+' ('+str(bug_rate)+'\%)'

    temp=[project,total_alerts,elim,act,traiged_bug]

    f.write('&'.join(str(x) for x in temp)+r'\\'+'\n')
