import pymysql
import sys
import numpy as np
import datetime
import re
import subprocess
import shlex
import os
from openpyxl import Workbook
mainpath=os.getcwd()
#read the project name
project=str(sys.argv[1])
path="/Users/nasifimtiaz/Desktop/new_data/"+sys.argv[2]

#check
# file reanaming backend/manager/modules/aaa/src/main/java/org/ovirt/engine/core/aaa/filters/SsoRestApiNegotiationFilter.java backend/manager/modules/aaa/src/main/java/org/ovirt/engine/core/aaa/filters/SsoRestApiNegotiationFilter.java rename backend/manager/modules/aaa/src/main/jav
# a/org/ovirt/engine/core/aaa/filters/{SSORestApiNegotiationFilter.java => SsoRestApiNegotiationFilter.java} (91%)
# file reanaming backend/manager/modules/dal/src/test/java/org/ovirt/engine/core/dao/VmStaticDaoTest.java backend/manager/modules/dal/src/test/java/org/ovirt/engine/core/dao/VmStaticDaoTest.java rename backend/manager/modules/dal/src/test/java/org/ovirt/engine/core/dao/{VmStaticDAOTest.java => VmStaticDaoTest.java} (99%)

#open sql connection 
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)



f= open(project+ "_analysis.txt","w")
os.chdir(path)

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
        f.write("count of total alert: "+str(total_alerts)+ '\n')
        
        query='''select count(*) as c from alerts where status="Fixed" and is_invalid=0 and stream="''' + project + '''";'''
        t=execute(query)[0]['c']
        f.write("eliminated bug: "+str(t)+" ")
        t=(float(t)/float(total_alerts))*100
        f.write("proportion: "+str(t)+ '\n')
        

        query='''select count(*) as c from alerts where is_invalid=0 and classification= "Bug" and stream="''' + project + '''";'''
        t=execute(query)[0]['c']
        f.write("marked bugs: "+str(t)+" ")
        t=(float(t)/float(total_alerts))*100
        f.write("proportion: "+str(t)+ '\n')

        query='''select count(*) as c from alerts where is_invalid=0 and classification= "False Positive" and stream="''' + project + '''";'''
        t=execute(query)[0]['c']
        f.write("false positive: "+str(t)+" ")
        t=(float(t)/float(total_alerts))*100
        f.write("proportion: "+str(t)+ '\n')

        query='''select count(*) as c from alerts where is_invalid=0 and classification= "Intentional" and stream="''' + project + '''";'''
        t=execute(query)[0]['c']
        f.write("intentional: "+str(t)+" ")
        t=(float(t)/float(total_alerts))*100
        f.write("proportion: "+str(t)+ '\n')

        query='''select count(*) as c from alerts where status="New" and is_invalid=0 and stream="''' + project + '''";'''
        t=execute(query)[0]['c']
        f.write("alive: "+str(t)+" ")
        t=(float(t)/float(total_alerts))*100
        f.write("proportion: "+str(t)+ '\n')


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
        f.write("number of other files alerts are: "+str(len(results))+'\n')
        
        #generate general reports
        query="select distinct status, count(*) as c from alerts where is_invalid=3 and stream='"+project+"' group by status;"
        temp=execute(query)
        f.write(str(temp)+'\n')

        #generate general reports
        query="select distinct classification, count(*) as c from alerts where is_invalid=3 and stream='"+project+"' group by classification;"
        temp=execute(query)
        f.write(str(temp)+'\n\n\n')

        #write the name of the other files
        query="select f.filepath_on_coverity from alerts a join files f on a.file_id=f.idfiles where a.is_invalid=3 and a.stream='"+project+"';"
        temp=execute(query)
        for t in temp:
                f.write(str(t)+'\n')
        
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
                stderr=subprocess.STDOUT,encoding="437").split("\n")
        
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
        return None


def detect_file_rename_delete_in_a_commit(sha,filepath,change_type):
        filepath=filepath[1:]
        if type(change_type)==str and (bool(re.search('MODIFY',change_type,re.I)) or bool(re.search('ADD',change_type,re.I))):
                return None
        if type(change_type)==str and bool(re.search('RENAME',change_type,re.I)):
                return 'renamed'
        else:
                lines=subprocess.check_output(
                        shlex.split("git show --summary "+sha), 
                stderr=subprocess.STDOUT,encoding="437").split('\n')
                for nextLine in lines:
                        #look for only short filename in lines
                        nextLine=nextLine.encode('ascii','ignore').decode()
                        if filepath.split("/")[-1] in nextLine:
                                if 'rename' in nextLine:
                                        return 'renamed'
                                elif 'delete' in nextLine:
                                        return 'deleted'
                return None 

def new_file_id_after_renaming(sha,filepath):
        filepath=filepath[1:]
        lines=subprocess.check_output(
                shlex.split("git show --summary "+sha), 
                stderr=subprocess.STDOUT,encoding="437").split('\n')
        rename_line=''

        filename=filepath.split("/")[-1]
        for nextLine in lines:
                if filename in nextLine and 'rename' in nextLine:
                        rename_line=nextLine
        # try:
        matchlist=re.findall('{[^{}]*}',rename_line)
        if len(matchlist)!=1:
                #need to discover the logic here
                print ("check ",sha,filepath,project,rename_line)

        try:
                temp=re.search("{(.*)}",rename_line).group(1)
                temp=temp.split("=>")
                old_file=temp[0].strip()
                new_file=temp[1].strip()
                rename_line=rename_line.strip()
                start=rename_line.find('{')
                end=rename_line.find('}')
                new_filepath=rename_line[:start]+new_file+rename_line[end+1:] 
                new_filepath=new_filepath.replace('//','/')
                new_filepath=new_filepath.split(' ')[1].strip()
                query="select idfiles from files where filepath_on_coverity='/"+new_filepath+"' and project='"+project+"';"
                return execute(query)[0]['idfiles']
        except Exception as e:
                print(e)
                return None

# first look for file_activity with the main affected file
def main_file_actionability():
        query=query="select * from alerts where is_invalid=0 and status='Fixed' and stream='"+project+"';"
        #"' and idalerts="+str(alert_id)
        all_alerts=execute(query)
        for alert in all_alerts:
                aid=alert["idalerts"]

                #initialize actionability columns with default values
                actionability=0
                marked_bug=None
                file_activity_around_fix=None
                single_fix_commit=None
                fix_commits=None
                deleted=None
                delete_commit=None
                renamed=None
                rename_commit=None
                transfered_alert_id=None
                suppression=None
                suppress_keyword=None
                suppress_commit=None
                
                classification=alert['classification']
                if bool(re.search('Bug',classification,re.I)):
                        marked_bug='yes'


                last_snapshot=str(alert["last_snapshot_id"])
                ## get last detected dates
                query="select date from snapshots where idsnapshots="+last_snapshot+" and stream='" +project +"';"
                last_detected_date=execute(query)[0]["date"]
                last_detected_date=last_detected_date.strftime("%Y-%m-%d") +" 00:00:00" #to maintain start of the day
                query="select date from snapshots where last_snapshot="+last_snapshot+" and stream='" +project +"';"
                first_not_detected_anymore_date=execute(query)[0]["date"]
                first_not_detected_anymore_date=first_not_detected_anymore_date.strftime("%Y-%m-%d") +" 23:59:59" #to maintain end of the day

                fid=alert["file_id"]
                #look at if there's a commit (both author and commit date) within above two dates
                query='''select * from filecommits fc join commits c on fc.commit_id=c.idcommits 
                        join files f on f.idfiles=fc.file_id
                        where
                        fc.file_id= ''' + str(fid) + ''' and ((c.commit_date >="''' +last_detected_date+ \
                        '''" and c.commit_date <="''' +first_not_detected_anymore_date +'''")
                        or (c.author_date >="''' +last_detected_date+ \
                        '''" and c.author_date <="''' +first_not_detected_anymore_date +'''"))
                        ;'''
                results=execute(query)

                if len(results)>0:
                        file_activity_around_fix='yes'

                        #check if the file is deleted or renamed (involved moved) in the last commit
                        last_commit=results[-1]
                        temp=detect_file_rename_delete_in_a_commit(last_commit['sha'],last_commit['filepath_on_coverity'],last_commit['change_type'])
                        if temp == 'deleted':
                                deleted='yes'
                                delete_commit=str(last_commit['idcommits'])
                        elif temp == 'renamed':
                                # find out if the alert was transitioned into a new alert_id
                                # how?
                                # look at the first_not_detected snapshot
                                # if there's a newly detected alert ( first_detected > last snapshot)
                                # and if it's in the renamed file with the same alert_type
                                renamed='yes'
                                rename_commit=str(last_commit['idcommits'])
                                new_file_id=new_file_id_after_renaming(last_commit['sha'],last_commit['filepath_on_coverity'])
                                if new_file_id:
                                        query="select * from alerts where first_detected > '"+last_detected_date+"' and first_detected <= '"+first_not_detected_anymore_date+"' \
                                                and file_id="+str(new_file_id) +" and bug_type="+str(alert['bug_type'])+";"
                                        temp_results=execute(query)
                                        if len(temp_results)==1:
                                                transfered_alert_id=temp_results[0]['idalerts']
                        else:
                                commits=[]
                                for item in results:
                                        c={}
                                        c['commit_id']=item['idcommits']
                                        c['sha']=item['sha']
                                        c['filepath']=item['filepath_on_coverity'][1:]
                                        c['msg']=item['message']
                                        commits.append(c)
                                for c in commits:
                                        #look for suppression keywords in commit diff
                                        suppression_word=search_suppression_keywords_in_commit_diffs(c['sha'],c['filepath'])
                                        if suppression_word!=None:
                                                suppression='yes'
                                                suppress_commit=str(c['commit_id'])
                                                suppress_keyword=suppression_word
                                                break
                                if suppress_commit==None:
                                        #developer fix
                                        if len(commits)==1:
                                                single_fix_commit=str(commits[0]['commit_id'])
                                        else:
                                                #look for keyword coverity, CID
                                                temp=[]
                                                for c in commits:
                                                        temp.append(str(c['commit_id']))
                                                        if (bool(re.search('coverity',c['msg'],re.I))) or (bool(re.search('CID',c['msg'],re.I))):
                                                                single_fix_commit=str(c['commit_id'])
                                                fix_commits=','.join(temp)
                        
                #determine actionability
                if marked_bug=='yes' or single_fix_commit!=None or fix_commits!=None:
                        actionability=1
                # print((str(aid),actionability,marked_bug,file_activity_around_fix,single_fix_commit,fix_commits,deleted, 
                #         delete_commit,renamed,rename_commit,transfered_alert_id,suppression,suppress_commit,suppress_keyword))
                try:
                        with connection.cursor() as cursor:
                                cursor.execute('insert into actionability values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', 
                                (str(aid),actionability,marked_bug,file_activity_around_fix,single_fix_commit,fix_commits,deleted, 
                                delete_commit,renamed,rename_commit,transfered_alert_id,suppression,suppress_commit,suppress_keyword))
                except Exception as e:
                        print(e)







## get alerts with no event history and make a temporary table for them 
def fixed_alerts_with_history():
        with connection.cursor() as cursor:
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
                cursor.execute(query)

                query="select * from alerts where stream='"+project+"' and is_invalid=0 and status='Fixed' and idalerts not in (select alert_id from alerts_with_no_history);"
                cursor.execute(query)
                return cursor.fetchall()

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

def developer_fix_report():
        query="select count(*) as c from alerts where is_invalid=0 and stream='"+project+"';"
        total=execute(query)[0]['c']

        query='''select count(*) as c from actionability ac 
                join alerts a 
                on ac.alert_id=a.idalerts
                where ac.actionable=1 
                and a.stream="'''+project+'''";'''
        fix=execute(query)[0]['c']

        query='''select count(*) as c from alert_commit_tracking ac 
                join alerts a 
                on ac.alert_id=a.idalerts
                where ac.fix_commit_id is not null
                and a.stream="'''+project+'''";'''
        fix_commit=execute(query)[0]['c']

        unactionable=total-fix

        f.write("\ndeveloper fix :"+str(fix)+" "+str((float(fix)/total)*100)+'\n')
        f.write("tracked fix commit for :"+str(fix_commit)+" "+str((float(fix_commit)/total)*100)+'\n')
        f.write("unactionable :"+str(unactionable)+" "+str((float(unactionable)/total)*100)+'\n')

def actionability_and_lifespan_report():
        query="select count(*) as c from alerts where is_invalid=0 and stream='"+project+"';"
        total_alerts=execute(query)[0]['c']
        #need to subtract new alerts that are alive for less the median lifespan of actionable alerts
        
        query='''select count(*) as c from actionability ac
                join alerts a 
                on a.idalerts=ac.alert_id
                where ac.actionability = 1
                and a.stream="''' + project + '"'
        actionable_count=execute(query)[0]['c']
        
        query='''select datediff(s.date,a.first_detected) as diff from actionability ac
                join alerts a 
                on a.idalerts=ac.alert_id
                join snapshots s
                on a.last_snapshot_id=s.idsnapshots
                where ac.actionability = 1
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
                and datediff(
                (select date
                from snapshots
                where stream="'''+project+'''"
                order by idsnapshots desc
                limit 1),
                first_detected
                ) <=''' +str(actionable_lifespan)
        too_new_to_count=execute(query)[0]['c']
        total_alerts-=too_new_to_count



        f.write("actionable bugs are: "+str(actionable_count)+'\n')
        f.write("median lifspan of actionable alerts are : "+str(actionable_lifespan)+'\n')
        f.write("actionablity rate: "+str((float(actionable_count)/total_alerts)*100)+'\n')

        query='''select datediff(s.date,a.first_detected) as diff from actionability ac
                join alerts a 
                on a.idalerts=ac.alert_id
                join snapshots s
                on a.last_snapshot_id=s.idsnapshots
                where ac.actionability = 1
                and a.classification="Bug"
                and a.stream="''' + project + '"'
        results=execute(query)
        temp=[]
        for item in results:
                temp.append(item['diff'])
        
        bug_lifespan=np.median(temp)
        f.write("median lifspan of  marked bug are : "+str(bug_lifespan)+'\n')

       #1 is for other-file alerts  
        query='''select datediff(s.date,a.first_detected) as diff 
                from alerts a 
                join snapshots s
                on a.last_snapshot_id=s.idsnapshots
                and a.is_invalid=3
                and a.status='Fixed'
                and a.stream="''' + project + '"'
        results=execute(query)
        temp=[]
        for item in results:
                temp.append(item['diff'])
        
        other_file_lifespan=np.median(temp)
        f.write("median lifspan of other-file alerts are : "+str(other_file_lifespan)+'\n')

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
        
        unactionable_lifespan=np.median(temp)
        f.write("median lifspan of unactionable alerts are : "+str(unactionable_lifespan)+'\n')

def manual_validation_file():
        os.chdir(mainpath)

        wb=Workbook()
        ws1=wb.create_sheet("Fix commits",0)
        query='''select a.idalerts,a.cid, b.type, f.filepath_on_coverity, ac.*
                from actionability ac
                join alerts a
                on a.idalerts=ac.alert_id 
                join files f
                on f.idfiles=a.file_id
                join bug_types b
                on b.idbug_types=a.bug_type
                where ac.actionability=1
                and (ac.single_fix_commit is not null or ac.fix_commits is not null)
                and a.stream="'''+project+'''"
                order by rand()
                limit 25'''
        results=execute(query)

        row=2
        for item in results:
                #get commit hashes
                commits=[]
                if item['single_fix_commit']!=None:
                        query="select * from commits where idcommits="+str(item['single_fix_commit'])
                        commits.append(execute(query)[0])
                else:
                        temp=str(item['fix_commits'])
                        temp=temp.split(',')
                        for t in temp:
                                query="select * from commits where idcommits="+str(t)
                                commits.append(execute(query)[0])
                for c in commits:    
                        ws1['A'+str(row)]=item['idalerts']
                        ws1['B'+str(row)]=item['cid']
                        ws1['C'+str(row)]=item['type']
                        ws1['D'+str(row)]=item['filepath_on_coverity']
                        ws1['E'+str(row)]=c['sha']
                        ws1['F'+str(row)]=c['message']
                        row+=1

        ws2=wb.create_sheet("Unactionable Alerts",1)

        query='''select a.idalerts,a.cid, b.type, f.filepath_on_coverity, ac.*
                from actionability ac
                join alerts a
                on a.idalerts=ac.alert_id 
                join files f
                on f.idfiles=a.file_id
                join bug_types b
                on b.idbug_types=a.bug_type
                where ac.actionability=0
                and (ac.file_deleted is null and ac.file_renamed is null)
                and a.stream="'''+project+'''"
                order by rand()
                limit 25'''
        results=execute(query)

        row=2
        for item in results:
                ws2['A'+str(row)]=item['idalerts']
                ws2['B'+str(row)]=item['cid']
                ws2['C'+str(row)]=item['type']
                ws2['D'+str(row)]=item['filepath_on_coverity']
                row+=1
        
        ws3=wb.create_sheet("Single Fix Commits",2)
        query='''select a.idalerts,a.cid, b.type, f.filepath_on_coverity, ac.*
                from actionability ac
                join alerts a
                on a.idalerts=ac.alert_id 
                join files f
                on f.idfiles=a.file_id
                join bug_types b
                on b.idbug_types=a.bug_type
                where ac.actionability=1
                and ac.single_fix_commit is not null
                and a.stream="'''+project+'''"
                order by rand()
                limit 25'''
        results=execute(query)

        row=2
        for item in results:
                #get commit hashes
                commits=[]
                if item['single_fix_commit']!=None:
                        query="select * from commits where idcommits="+str(item['single_fix_commit'])
                        commits.append(execute(query)[0])
                for c in commits:    
                        ws3['A'+str(row)]=item['idalerts']
                        ws3['B'+str(row)]=item['cid']
                        ws3['C'+str(row)]=item['type']
                        ws3['D'+str(row)]=item['filepath_on_coverity']
                        ws3['E'+str(row)]=c['sha']
                        ws3['F'+str(row)]=c['message']
                        row+=1

        wb.save('Project_'+project+'.xlsx')

def invalidate_file_renamed_alerts():
        '''look for alerts in actionability that has renamed 'yes'
        and invalidate them to 4 in alerts '''
        query='''update alerts 
                set is_invalid=4
                where stream= "''' +project+'''"
                and idalerts in
                (select alert_id from actionability 
                where file_renamed="yes")'''
        execute(query)
        '''if they have a transferred alert id then adjust first_detected'''
        query='''select * from actionability ac
                join alerts a
                on a.idalerts = ac.alert_id
                where ac.file_renamed='yes'
                and a.stream="'''+project+'''"
                and transfered_alert_id is not null;'''
        results=execute(query)
        for item in results:
                old_id=item['alert_id']
                new_id=item['transfered_alert_id']
                query='''update alerts 
                        set first_detected=(
                        select first_detected from 
                        (select first_detected from alerts
                        where idalerts ='''+str(old_id)+''') as sub)
                        where idalerts=''' +str(new_id)
                with connection.cursor() as cursor:
                        cursor.execute(query)
                        print(cursor.rowcount)

def file_renaming_info():
        #we search this only for fixed alerts as
        #alerts are supposed to be eliminated 
        #when the file is renamed (deleted)
        query='''select count(*) as c
                from alerts
                where stream= "''' +project+'''"
                and idalerts in
                (select alert_id from actionability 
                where file_renamed="yes")''' 
        c=execute(query)[0]['c']
        f.write('the number of alerts that are invalidated due to file renaming is: '+str(c))

        query='''select count(*) as c
                from alerts
                where stream= "''' +project+'''"
                and idalerts in
                (select alert_id from actionability 
                where file_renamed="yes"
                and transfered_alert_id is not null)''' 
        c=execute(query)[0]['c']
        f.write('the number of alerts that are transfered due to file renaming is: '+str(c))

def patch_complexity():
        query='''select count(*) as c
                from actionability ac
                join alerts a 
                on a.idalerts=ac.alert_id
                where a.stream="'''+project +'''"
                and ac.single_fix_commit is not null'''
        fix_commit_tracked=execute(query)[0]['c']
        f.write("fix commit tracked for alerts: "+str(fix_commit_tracked)+'\n')

        query='''select * from
                (select distinct ac.single_fix_commit, count(*)  as c
                from actionability ac
                join alerts a
                on ac.alert_id=a.idalerts 
                where a.stream="'''+project+'''"
                and ac.single_fix_commit is not null
                and a.is_invalid=0
                group by ac.single_fix_commit) as fix
                join commits c
                on fix.single_fix_commit=c.idcommits'''
        results=execute(query)
        files=[]
        loc=[]
        for item in results:
                c=item['c']
                file_count=float(item['affected_files_count'])
                l=float(item['net_lines_added']+item['net_lines_removed'])
                files.append(file_count/c)
                loc.append(l/c)
        files.sort()
        loc.sort()
        f.write("median affected files: "+str(np.median(files))+'\n')
        f.write("median net LOC change: "+str(np.median(loc))+'\n')


        query='''select * from
        (select ac.single_fix_commit, a.file_id, count(*)  as c
        from actionability ac
        join alerts a
        on ac.alert_id=a.idalerts 
        where a.stream="'''+project+'''"
        and ac.single_fix_commit is not null
        and a.is_invalid=0
        group by ac.single_fix_commit,a.file_id) as fix
        join filecommits fc
        on fix.single_fix_commit=fc.commit_id'''
        results=execute(query)
        loc=[]
        for item in results:
                if item['lines_added']==None or item['lines_removed']==None:
                        continue
                c=item['c']
                l=float(item['lines_added']+item['lines_removed'])
                loc.append(l/c)
        loc.sort()
        f.write("median in-file LOC change: "+str(np.median(loc)))

def methodology_infos():
        get_general_report()
        # need to give info on data cleaning
        file_renaming_info()

def update_fix_commit_infos():
        #TODO: one commit that fixes multiple warnings?
        query='''select distinct ac.single_fix_commit, c.*,f.* from actionability ac
                join alerts a
                on ac.alert_id=a.idalerts
                join commits c
                on c.idcommits = ac.single_fix_commit
                join files f
                on f.idfiles=a.file_id
                where ac.single_fix_commit is not null
                and ac.actionability=1
                and a.stream ="'''+project+'"'
        results=execute(query)

        patches=[]
        
        for item in results:
                d={}
                sha=item['sha']
                cid=item['idcommits']
                filepath=item['filepath_on_coverity'][1:]
                fid=item['idfiles']
                lines=subprocess.check_output(
                        shlex.split('git show --stat '+sha),
                        encoding="437"
                ).split('\n')
                line=lines[-2].strip()
                temp=line.split(',')
                info=[]
                query=''
                if len(temp)==3:
                        for t in temp:
                                t=t.strip()
                                info.append(t.split(' ')[0])
                        #update commit table
                        query='update commits set affected_files_count='+info[0]+',net_lines_added='+info[1]+',net_lines_removed='+info[2]+' where idcommits='+str(cid)
                elif len(temp)==2:
                        if 'insert' in line:
                                for t in temp:
                                        t=t.strip()
                                        info.append(t.split(' ')[0])
                                #update commit table
                                query='update commits set affected_files_count='+info[0]+',net_lines_added='+info[1]+',net_lines_removed=0 where idcommits='+str(cid)
                        elif 'delet' in line:
                                for t in temp:
                                        t=t.strip()
                                        info.append(t.split(' ')[0])
                                #update commit table
                                query='update commits set affected_files_count='+info[0]+',net_lines_added=0,net_lines_removed='+info[1]+' where idcommits='+str(cid)
                execute(query)  



def lifespan_vs_complexity():
        query='''select idalerts, datediff(s.date,a.first_detected) as diff from actionability ac
                join alerts a 
                on a.idalerts=ac.alert_id
                join snapshots s
                on a.last_snapshot_id=s.idsnapshots
                where ac.actionability = 1
                and a.stream="''' + project + '"'


if __name__ == "__main__":
        # processing functions
        main_file_actionability()
        invalidate_file_renamed_alerts()
        
        # reporting functions
        methodology_infos()
        get_alert_infos()
        actionability_and_lifespan_report()
        
        update_fix_commit_infos()
        patch_complexity()
        manual_validation_file()

        alerts_from_other_files()