import pymysql
import sys
import numpy as np
import datetime

#read the project name
project=str(sys.argv[1])

#open sql connection 
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)



f= open(project+ "_analysis.txt","w")


def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results=cursor.fetchall()
    return results

# # total number on snapshots, start date, and end_date, median interval between snapshots
# query='''select count(*) as c
#         from snapshots
#         where 
#         stream="''' + project + '''";'''
# snapshot_count=execute(query)[0]["c"]
# f.write("total snapshots = " + str(snapshot_count))

# query='''select start_date, end_date from projects 
#         where name="''' + project + '''";'''
# start_date=execute(query)[0]["start_date"]
# end_date=execute(query)[0]["end_date"]
# f.write("start date and end dates are: "+str(start_date)+", "+str(end_date))

# query='''select datediff(s1.date,s2.date) as diff
#         from snapshots s1
#         join snapshots s2
#         on s1.last_snapshot=s2.idsnapshots
#         where s1.last_snapshot is not null and
#         s2.stream="'''+project+ \
#         '''" and s1.stream="''' + project + '''";'''
# datediffs=execute(query)
# temp=[]
# for d in datediffs:
#     temp.append(d["diff"])
# median_interval=np.median(temp)
# avg_interval= np.mean(temp)
# f.write("median and average interval between snapshots are: "+str(median_interval)+", "+str(avg_interval))

# # get alert infos
# query='''select * from alerts
# where status="Fixed" and is_invalid=0 and stream="''' + project + '''";'''
# all_alerts=execute(query)
# f.write("total alerts are: "+str(len(all_alerts)))

# first look for file_activity with the main affected file
def main_file_fix_activity(all_alerts):
        for alert in all_alerts:
                aid=alert["idalerts"]
                last_snapshot=str(alert["last_snapshot_id"])

                ## get last detected dates
                query="select date from snapshots where idsnapshots="+last_snapshot+" and stream='" +project +"';"
                last_detected_date=execute(query)[0]["date"]
                last_detected_date=last_detected_date.strftime("%Y-%m-%d")
                query="select date from snapshots where last_snapshot="+last_snapshot+" and stream='" +project +"';"
                first_not_detected_anymore_date=execute(query)[0]["date"]
                first_not_detected_anymore_date=first_not_detected_anymore_date.strftime("%Y-%m-%d")

                fid=alert["file_id"]
                
                #look at if there's a commit within above two dates
                query='''select * from filecommits f join commits c on f.commit_id=c.idcommits where
                        f.file_id= ''' + str(fid) + ''' and c.commit_date >="''' +last_detected_date+ \
                        '''" and c.commit_date <="''' +first_not_detected_anymore_date +'";'
                results=execute(query)
                query=""
                if len(results)>0:
                        cid="null"
                        if len(results)==1:
                                cid=str(results[0]["idcommits"])
                        query="insert into alert_commit_tracking values(" +str(aid)+",null,'yes',null,"+cid+");"
                else:
                        query="insert into alert_commit_tracking values(" +str(aid)+",null,'no',null,null);"
                try:
                        print(query)
                        execute(query)
                except Exception as e:
                        print(e)







## get alerts with no event history and make a temporary table for them 
def fixed_alerts_with_history():
        query = '''create temporary table alerts_with_no_history
                select alert_id
                from
                (select a.idalerts as id, count(*) as c
                from alerts a
                join occurrences o
                on a.idalerts=o.alert_id
                where a.stream="''' + project + \
                '''" group by a.idalerts) as event_count
                join occurrences o
                on event_count.id=o.alert_id
                where event_count.c=1 
                and o.line_number=1 '''
        execute(query)

        query="select * from alerts where stream='"+project+"' and status='Fixed' and idalerts not in (select alert_id from alerts_with_no_history);"
        temp=execute(query)
        return temp

def all_file_fix_activity(all_alerts):
        for alert in all_alerts:
                aid=str(alert['idalerts'])
                print (aid)
                query="select * from occurrences where alert_id="+aid
                occurrences=execute(query)
                locations={}
                for o in occurrences:
                        fid=o["file_id"]
                        if fid is None:
                                continue
                        line=o["line_number"]
                        if fid not in locations.keys():
                                locations[fid]=[]
                        locations[fid].append(line)

                actionable=False
                commits=[]

                last_snapshot=str(alert["last_snapshot_id"])
                ## get last detected dates
                query="select date from snapshots where idsnapshots="+last_snapshot+" and stream='" +project +"';"
                last_detected_date=execute(query)[0]["date"]
                last_detected_date=last_detected_date.strftime("%Y-%m-%d") + " 00:00:00"
                query="select date from snapshots where last_snapshot="+last_snapshot+" and stream='" +project +"';"
                first_not_detected_anymore_date=execute(query)[0]["date"]
                first_not_detected_anymore_date=first_not_detected_anymore_date.strftime("%Y-%m-%d") + " 00:00:00"

                for fid in locations.keys():
                        #look at if there's a commit within above two dates
                        print("file id is: ",fid)
                        query='''select * from filecommits f join commits c on f.commit_id=c.idcommits where
                                f.file_id= ''' + str(fid) + ''' and c.commit_date >="''' +last_detected_date+ \
                                '''" and c.commit_date <="''' +first_not_detected_anymore_date +'";'
                        results=execute(query)
                        if len(results)>0:
                                actionable=True
                                for item in results:
                                        commits.append(item)
                print(commits)


all_file_fix_activity(fixed_alerts_with_history())
f.close()