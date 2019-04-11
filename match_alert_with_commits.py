import pymysql
import sys

#get cmd line arguments
project=sys.argv[1]

connection = pymysql.connect(host='localhost', user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)
def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results=cursor.fetchall()
    return results

#create a table with alerts_with_no_event_history
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

##fixed alerts with no event history
query='''select *
        from alerts a 
        join alerts_with_no_history nohis
        on a.idalerts=nohis.alert_id
        where a.status='Fixed'
        and a.stream="''' + project +'"'
fixed_nohis=execute(query)

## fixed alerts with detailed event history
query='''select *
        from alerts a 
        where a.status='Fixed'
        and a.stream="''' + project + \
        '''" and idalerts not in 
        (select alert_id
        from alerts_with_no_history)'''
fixed_withhis=execute(query)

print(len(fixed_nohis),len(fixed_withhis))


## first do with the event
for item in fixed_withhis:
    id=item["idalerts"]
    last_snapshot=str(item["last_snapshot_id"])

    ## get last detected dates
    query="select date from snapshots where idsnapshots="+last_snapshot+" and stream='" +project +"';"
    last_detected_date=execute(query)[0]["date"]
    query="select date from snapshots where last_snapshot="+last_snapshot+" and stream='" +project +"';"
    first_not_detected_anymore_date=execute(query)[0]["date"]

    ## get all the files associated and their line numbers
    query="select * from occurrences where alert_id="+str(id)
    temp=execute(query)
    locations={}
    for t in temp:
        fid=t["file_id"]
        line=int(t["line_number"])
        if fid not in locations.keys():
            locations[fid]=[]
        locations[fid].append(line)
    
    print(id,locations,last_detected_date,first_not_detected_anymore_date)
    #check if there's any commits around the date?




