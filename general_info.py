import pymysql
import numpy as np


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

projects=['Linux','Firefox','Samba','Kodi','Ovirt-engine']

def actionable_alert_report():
    f=open('temp.txt','w')
    for project in projects:
        query='''select * from alerts where is_invalid=0 and stream="''' + project + '''";'''
        all_alerts=execute(query)
        total_alerts=len(all_alerts)
        
        query='''select count(*) as c from alerts where status="Fixed" and is_invalid=0 and stream="''' + project + '''";'''
        t=execute(query)[0]['c']
        eliminated=str(t)
        t=round((float(t)/float(total_alerts))*100,1)
        eliminated+=" ("+str(t)+"\\%)"
        
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
        adjusted_total=total_alerts-too_new_to_count

        actionable=str(actionable_count)
        t=round((float(actionable_count)/adjusted_total)*100,1)
        actionable+=" ("+str(t)+"\\%)"

        query='''select count(*) as c from alerts where is_invalid=0 and classification= "Bug" and stream="''' + project + '''";'''
        t=execute(query)[0]['c']
        bug=str(t)
        t=round((float(t)/float(total_alerts))*100,1)
        bug+=" ("+str(t)+"\\%)"

        temp=[project,total_alerts,eliminated,actionable,bug]
        f.write('&'.join(str(x) for x in temp)+r'\\'+'\n')

def unactionable_report():
    f=open('temp.txt','w')
    for project in projects:
        query='''select * from alerts where is_invalid=0 and stream="''' + project + '''";'''
        all_alerts=execute(query)
        total_alerts=len(all_alerts)
        
        query='''select count(*) as c from alerts where status="Fixed" and is_invalid=0 and stream="''' + project + '''";'''
        t=execute(query)[0]['c']
        eliminated=str(t)
        t=round((float(t)/float(total_alerts))*100,1)
        eliminated+=" ("+str(t)+"\\%)"
        
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
        adjusted_total=total_alerts-too_new_to_count

        total_alerts=adjusted_total-actionable_count
        u=total_alerts

        query='''select count(*) as c from alerts where is_invalid=0 
                and classification= "False Positive"
                and stream="''' + project + '''";'''
        t=execute(query)[0]['c']
        u-=t
        fp=str(t)
        t=round((float(t)/float(total_alerts))*100,1)
        fp+=" ("+str(t)+"\\%)"
        
        query='''select count(*) as c from alerts where is_invalid=0 
                and classification= "Intentional"
                and stream="''' + project + '''";'''
        t=execute(query)[0]['c']
        u-=t
        intentional=str(t)
        t=round((float(t)/float(total_alerts))*100,1)
        intentional+=" ("+str(t)+"\\%)"

        query='''select count(*) as c from alerts a
                join actionability ac
                on a.idalerts=ac.alert_id
                where ac.file_deleted="yes"
                and a.stream="'''+project+'"'
        t=execute(query)[0]['c']
        u-=t
        file_deleted=str(t)
        t=round((float(t)/float(total_alerts))*100,1)
        file_deleted+=" ("+str(t)+"\\%)"
        
        query='''select count(*) as c from alerts a
                join actionability ac
                on a.idalerts=ac.alert_id
                where ac.suppression="yes"
                and a.stream="'''+project+'"'
        t=execute(query)[0]['c']
        u-=t
        suppression=str(t)
        t=round((float(t)/float(total_alerts))*100,1)
        suppression+=" ("+str(t)+"\\%)"
        
        query='''select count(*) as c
                from alerts 
                where stream="'''+project+'''"
                and status='New'
                and is_invalid=0'''
        t=execute(query)[0]['c']
        t-=too_new_to_count
        u-=t
        alive=str(t)
        t=round((float(t)/float(total_alerts))*100,1)
        alive+=" ("+str(t)+"\\%)"

        t=u
        unknown=str(t)
        t=round((float(t)/float(total_alerts))*100,1)
        unknown+=" ("+str(t)+"\\%)"

        temp=[project,total_alerts,alive,fp,intentional,file_deleted,suppression,unknown]
        f.write('&'.join(str(x) for x in temp)+r'\\'+'\n')
if __name__ == "__main__":
    unactionable_report()
    