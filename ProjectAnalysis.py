import pymysql
import sys
import numpy as np

#read the project name
project=str(sys.argv[1])

#open sql connection 
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='890coverity',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)



f= open(project+ "_analysis.txt","w")


def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results=cursor.fetchall()
    return results

# total number on snapshots, start date, and end_date, median interval between snapshots
query='''select count(*) as c
        from snapshots
        where 
        stream="''' + project + '''";'''
snapshot_count=execute(query)[0]["c"]

query='''select start_date, end_date from projects 
        where name="''' + project + '''";'''
start_date=execute(query)[0]["start_date"]
end_date=execute(query)[0]["end_date"]

query='''select datediff(s1.date,s2.date) as diff
        from snapshots s1
        join snapshots s2
        on s1.last_snapshot=s2.idsnapshots
        where s1.last_snapshot is not null and
        s2.stream="'''+project+ \
        '''" and s1.stream="''' + project + '''";'''
datediffs=execute(query)
temp=[]
for d in datediffs:
    temp.append(d["diff"])
print(temp)
median_interval=np.median(temp)
avg_interval= np.mean(temp)

print(median_interval,avg_interval)

# get alert infos
query='''select count(*) as c from alerts
where stream="''' + project + '''";'''
total_alerts=execute(query)[0]["c"]

## get alerts with no event history and make a temporary table for them 

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

query="select count(*) as c from alerts_with_no_history"
alerts_with_no_history= execute(query)[0]["c"]



f.close()