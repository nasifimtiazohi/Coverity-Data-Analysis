import pymysql
import numpy as np


#open sql connection 
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan_sandbox',
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

def get_general_report():
        # total number on snapshots, start date, and end_date, median interval between snapshots
        query = '''select count(*) as c
                from snapshots
                where
                stream="''' + project + '''";'''
        snapshot_count = execute(query)[0]["c"]
        f.write("total snapshots = " + str(snapshot_count) + '\n')

        query = '''select start_date, end_date from projects
                where name="''' + project + '''";'''
        start_date = execute(query)[0]["start_date"]
        end_date = execute(query)[0]["end_date"]
        f.write("start date and end dates are: " +
                str(start_date)+", "+str(end_date) + '\n')

        query = '''select datediff(s1.date,s2.date) as diff
                from snapshots s1
                join snapshots s2
                on s1.last_snapshot=s2.idsnapshots
                where s1.last_snapshot is not null and
                s2.stream="'''+project + \
                '''" and s1.stream="''' + project + '''";'''
        datediffs = execute(query)
        temp = []
        for d in datediffs:
                temp.append(d["diff"])
        median_interval = np.median(temp)
        avg_interval = np.mean(temp)
        f.write("median and average interval between snapshots are: " +
                str(median_interval)+", "+str(avg_interval) + '\n')


def get_alert_infos():
        query = '''select * from alerts where is_invalid=0 and stream="''' + project + '''";'''
        all_alerts = execute(query)
        total_alerts = len(all_alerts)
        f.write("count of total alert: "+str(total_alerts) + '\n')

        query = '''select count(*) as c from alerts where status="Fixed" and is_invalid=0 and stream="''' + \
                                project + '''";'''
        t = execute(query)[0]['c']
        f.write("eliminated alerts: "+str(t)+" ")
        t = (float(t)/float(total_alerts))*100
        f.write("proportion: "+str(t) + '\n')

        query = '''select count(*) as c from alerts where is_invalid=0 and classification= "Bug" and stream="''' + \
                                project + '''";'''
        t = execute(query)[0]['c']
        f.write("marked bugs: "+str(t)+" ")
        t = (float(t)/float(total_alerts))*100
        f.write("proportion: "+str(t) + '\n')

        query = '''select count(*) as c from alerts where is_invalid=0 and classification= "False Positive" and stream="''' + project + '''";'''
        t = execute(query)[0]['c']
        f.write("false positive: "+str(t)+" ")
        t = (float(t)/float(total_alerts))*100
        f.write("proportion: "+str(t) + '\n')

        query = '''select count(*) as c from alerts where is_invalid=0 and classification= "Intentional" and stream="''' + project + '''";'''
        t = execute(query)[0]['c']
        f.write("intentional: "+str(t)+" ")
        t = (float(t)/float(total_alerts))*100
        f.write("proportion: "+str(t) + '\n')

        query = '''select count(*) as c from alerts where status="New" and is_invalid=0 and stream="''' + \
                                project + '''";'''
        t = execute(query)[0]['c']
        f.write("alive: "+str(t)+" ")
        t = (float(t)/float(total_alerts))*100
        f.write("proportion: "+str(t) + '\n')


def alerts_from_other_files():
        f.write('\n\n')
        # get alerts from files which never existed in the git history
        # change those alerts invalidity to 3
        query = '''update alerts
                set is_invalid=3
                where idalerts in
                (select idalerts from
                (select distinct a.idalerts
                from files f
                join alerts a
                on f.idfiles=a.file_id
                where f.idfiles not in
                (select distinct f.idfiles
                from files f
                join filecommits fc
                on f.idfiles=fc.file_id
                where f.project="''' + project+'''")
                and f.project = "''' + project + '''" and a.is_invalid=0)as sub);'''
        with connection.cursor() as cursor:
                cursor.execute(query)
                print("alerts from other files count affected: ", cursor.rowcount)

        query = "select * from alerts where is_invalid=3 and stream='"+project+"';"
        results = execute(query)
        f.write("number of other files alerts are: "+str(len(results))+'\n')

        # generate general reports
        query = "select distinct status, count(*) as c from alerts where is_invalid=3 and stream='" + \
                                               project+"' group by status;"
        temp = execute(query)
        f.write(str(temp)+'\n')

        # generate general reports
        query = "select distinct classification, count(*) as c from alerts where is_invalid=3 and stream='" + \
                                                       project+"' group by classification;"
        temp = execute(query)
        f.write(str(temp)+'\n\n\n')

        # #write the name of the other files
        # query="select f.filepath_on_coverity from alerts a join files f on a.file_id=f.idfiles where a.is_invalid=3 and a.stream='"+project+"';"
        # temp=execute(query)
        # for t in temp:
        #         f.write(str(t)+'\n')
if __name__ == "__main__":
    unactionable_report()
    