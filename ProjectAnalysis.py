import pymysql
import sys
import numpy as np
import datetime
import re
import subprocess
import shlex
import os

#read the project name
project=str(sys.argv[1])
path="/Users/nasifimtiaz/Desktop/new_data/"+sys.argv[2]
os.chdir(path)

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
    
def get_general_report():
        # total number on snapshots, start date, and end_date, median interval between snapshots
        query='''select count(*) as c
                from snapshots
                where 
                stream="''' + project + '''";'''
        snapshot_count=execute(query)[0]["c"]
        f.write("total snapshots = " + str(snapshot_count) + '\n')

        query='''select start_date, end_date from projects 
                where name="''' + project + '''";'''
        start_date=execute(query)[0]["start_date"]
        end_date=execute(query)[0]["end_date"]
        f.write("start date and end dates are: "+str(start_date)+", "+str(end_date)+ '\n')

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
        median_interval=np.median(temp)
        avg_interval= np.mean(temp)
        f.write("median and average interval between snapshots are: "+str(median_interval)+", "+str(avg_interval)+ '\n')

# # get alert infos
def get_alert_infos():
        query='''select * from alerts where is_invalid=0 and stream="''' + project + '''";'''
        all_alerts=execute(query)
        total_alerts=len(all_alerts)

        query='''select count(*) as c from alerts where is_invalid=0 and classification= "Bug" and stream="''' + project + '''";'''
        marked_bug=(float(execute(query)[0]['c'])/ float(total_alerts))*100

        query='''select count(*) as c from alerts where is_invalid=0 and classification= "False Positive" and stream="''' + project + '''";'''
        marked_fp=(float(execute(query)[0]['c'])/ float(total_alerts))*100

        query='''select count(*) as c from alerts where is_invalid=0 and classification= "Intentional" and stream="''' + project + '''";'''
        marked_intentional=(float(execute(query)[0]['c'])/ float(total_alerts))*100

        query='''select count(*) as c from alerts where status="Fixed" and is_invalid=0 and stream="''' + project + '''";'''
        eliminated=(float(execute(query)[0]['c'])/ float(total_alerts))*100

        query='''select count(*) as c from alerts where status="New" and is_invalid=0 and stream="''' + project + '''";'''
        alive=(float(execute(query)[0]['c'])/ float(total_alerts))*100

        f.write("count of total alert: "+str(total_alerts)+ '\n')
        f.write("count of eliminated: "+str(eliminated)+ '\n')
        f.write("count of marked bug: "+str(marked_bug)+ '\n')
        f.write("count of marked FP: "+str(marked_fp)+ '\n')
        f.write("count of marked intetional: "+str(marked_intentional)+ '\n')
        f.write("count of alive alerts: "+str(alive)+ '\n')

def alerts_from_other_files():
        f.write('\n\n')
        #get alerts from files which never existed in the git history
        ##change those alerts invalidity to 3
        query='''update alerts
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
                where f.project="''' +project+'''")
                and f.project = "''' +project+ '''" and a.is_invalid=0)as sub);'''
        execute(query)

        query="select * from alerts where is_invalid=3 and stream='"+project+"';"
        results=execute(query)
        f.write(str(len(results))+'\n')
        
        #generate general reports
        query="select distinct status, count(*) as c from alerts where is_invalid=3 and stream='"+project+"' group by status;"
        temp=execute(query)
        f.write(str(temp)+'\n')

        #generate general reports
        query="select distinct classification, count(*) as c from alerts where is_invalid=3 and stream='"+project+"' group by classification;"
        temp=execute(query)
        f.write(str(temp)+'\n')
        
def search_suppression_keywords_in_commit_diffs(sha,filepath):
        keywords=[
                r'coverity\[.*\]',
                r'/\* fall through \*/',
                '@OverridersMustCall', '@OverridersNeedNotCall',
                '@CheckReturnValue',
                '@GuardedBy',
                '@SuppressWarnings',
                '@CheckForNull',
                '@Tainted', '@NotTainted',
                '@SensitiveData',
        ]
        lines = subprocess.check_output(
                shlex.split('git show '+sha+' -- '+filepath), 
                stderr=subprocess.STDOUT).split("\n")
        
        for nextLine in lines:
                if bool(re.match('\+', nextLine,re.I)):
                        for keyword in keywords:
                                if bool(re.search(keyword,nextLine,re.I)):
                                        #found suppression word
                                        if keyword==r'coverity\[.*\]':
                                                temp=re.search(r'coverity\[(.*)\]',nextLine,re.I).group(1)
                                                return 'coverity['+temp+']'
                                        elif keyword==r'/\* fall through \*/':
                                                return '/* fall through */'
                                        else:
                                                return keyword
                else:
                        pass
        return False


        

# first look for file_activity with the main affected file
def main_file_fix_activity(all_alerts):
        query=query="select * from alerts where is_invalid=0 ans status='Fixed' and stream='"+project+"';"
        all_alerts=execute(query)
        for alert in all_alerts:
                aid=alert["idalerts"]
                last_snapshot=str(alert["last_snapshot_id"])

                ## get last detected dates
                query="select date from snapshots where idsnapshots="+last_snapshot+" and stream='" +project +"';"
                last_detected_date=execute(query)[0]["date"]
                last_detected_date=last_detected_date.strftime("%Y-%m-%d") +" 00:00:00" #to maintain start of the day
                query="select date from snapshots where last_snapshot="+last_snapshot+" and stream='" +project +"';"
                first_not_detected_anymore_date=execute(query)[0]["date"]
                first_not_detected_anymore_date=first_not_detected_anymore_date.strftime("%Y-%m-%d") +" 23:59:59" #to maintain end of the day

                fid=alert["file_id"]
                
                #look at if there's a commit within above two dates
                query='''select * from filecommits f join commits c on f.commit_id=c.idcommits where
                        f.file_id= ''' + str(fid) + ''' and c.commit_date >="''' +last_detected_date+ \
                        '''" and c.commit_date <="''' +first_not_detected_anymore_date +'";'
                results=execute(query)

                ##needs change. Firs look if exist, may need to update
                if len(results)>0:
                        commits=[]
                        for item in results:
                                c={}
                                c['commit_id']=item['idcommits']
                                c['sha']=item['sha']
                                c['filepath']=item['filepath_on_coverity'][1:]
                                commits.append(c)
                        for c in commits:
                                #look for suppression keywords in commit diff
                                pass
                        #query="insert into alert_commit_tracking values(" +str(aid)+",null,'yes',null,"+cid+");"
                else:
                        query="insert into alert_commit_tracking values(" +str(aid)+",null,'no',null,null,null.null);"
                # try:
                #         print(query)
                #         execute(query)
                # except Exception as e:
                #         print(e)







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

def all_file_fix_activity():
        query=query="select * from alerts where is_invalid=0 ans status='Fixed' and stream='"+project+"';"
        all_alerts=execute(query)
        for alert in all_alerts:
                aid=str(alert['idalerts'])
                cid=str(alert['cid'])
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
                print(aid,commits)

if __name__ == "__main__":
        # get_general_report()
        # get_alert_infos()
        #alerts_from_other_files()
        print(search_suppression_keywords_in_commit_diffs("7741d8254e0e15be91279a74627090f134412d0b","xbmc/utils/StringUtils.h"))

f.close()