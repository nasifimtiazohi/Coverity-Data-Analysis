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

# save the main path from where this script is running
mainpath = os.getcwd()

# read the project name
project = str(sys.argv[1])
path = "/Users/nasifimtiaz/Desktop/new_data/"+sys.argv[2]
start=sys.argv[3]
end=sys.argv[4]

# open sql connection
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)


f = open(project + "_brand_new_analysis.txt", "w")
os.chdir(path)


def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()
    return results


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

# # get alert infos


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


def search_suppression_keywords_in_commit_diffs(sha, filepath):
        keywords = [
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
                stderr=subprocess.STDOUT, encoding="437").split("\n")

        for nextLine in lines:
                if bool(re.match('\+', nextLine, re.I)):
                        for keyword in keywords:
                                if bool(re.search(keyword, nextLine, re.I)):
                                        # found suppression word
                                        if keyword == r'coverity\[.*\]':
                                                temp = re.search(
                                                    r'coverity\[(.*)\]', nextLine, re.I).group(1)
                                                return 'coverity['+temp+']'
                                        elif keyword == r'/\* fall through \*/':
                                                return '/* fall through */'
                                        else:
                                                return keyword
                else:
                        pass
        return None


def detect_file_rename_delete_in_a_commit(sha, filepath, change_type):
        filepath = filepath[1:]
        if type(change_type) == str and (bool(re.search('MODIFY', change_type, re.I)) or bool(re.search('ADD', change_type, re.I))):
                return None
        if type(change_type) == str and bool(re.search('RENAME', change_type, re.I)):
                return 'renamed'
        else:
                lines = subprocess.check_output(
                        shlex.split("git show --summary "+sha),
                stderr=subprocess.STDOUT, encoding="437").split('\n')
                for nextLine in lines:
                        # look for only short filename in lines
                        nextLine = nextLine.encode('ascii', 'ignore').decode()
                        if filepath.split("/")[-1] in nextLine:
                                if 'rename' in nextLine:
                                        return 'renamed'
                                elif 'delete' in nextLine:
                                        return 'deleted'
                return None


def new_file_id_after_renaming(sha, filepath):
        filepath = filepath[1:]
        lines = subprocess.check_output(
                shlex.split("git show --summary "+sha),
                stderr=subprocess.STDOUT, encoding="437").split('\n')
        rename_line = ''

        filename = filepath.split("/")[-1]
        for nextLine in lines:
                # renaming info in commit message can ruin string matching logic
                # however apartfrom rename, filename, and =>; git info also contain proportion with a %
                # so checking all those 4 conditions in trying to be more accurate
                if filename in nextLine and 'rename' in nextLine and '=>' in nextLine and '%' in nextLine:
                        rename_line = nextLine
        try:
                matchlist = re.findall('{[^{}]*}', rename_line)
                # being more restrictive (prolly not necessary) in having {} in this logic
                if len(matchlist) == 1 and '{' in rename_line and '}' in rename_line:
                        temp = re.search("{(.*)}", rename_line).group(1)
                        temp = temp.split("=>")
                        old_file = temp[0].strip()
                        new_file = temp[1].strip()
                        rename_line = rename_line.strip()
                        start = rename_line.find('{')
                        end = rename_line.find('}')
                        new_filepath = rename_line[:start] + \
                            new_file+rename_line[end+1:]
                        new_filepath = new_filepath.replace('//', '/')
                        new_filepath = new_filepath.split(' ')[1].strip()
                        query = "select idfiles from files where filepath_on_coverity='/" + \
                            new_filepath+"' and project='"+project+"';"
                        return execute(query)[0]['idfiles']
                # when the full name or filepath has been changed
                elif len(matchlist) == 0:
                        rename_line = rename_line.strip()
                        temp = rename_line.split('=>')
                        old_file = temp[0].strip()
                        old_file = old_file.split(' ')[1].strip()
                        new_file = temp[1].strip()
                        new_filepath = new_file.split(' ')[0].strip()
                        query = "select idfiles from files where filepath_on_coverity='/" + \
                            new_filepath+"' and project='"+project+"';"
                        return execute(query)[0]['idfiles']
                else:
                        return None
        except Exception as e:
                print("exception in rename discovery", e, rename_line)
                return None


def get_merged_date(id, sha):
        query='select * from merge_date where commit_id='+str(id)
        results=execute(query)
        if len(results)>0:
                return results[0]['merge_date'].strftime("%Y-%m-%d %H:%M:%S")

        query='select * from commits where idcommits='+str(id)
        commit=execute(query)[0]

        lines = subprocess.check_output(
            shlex.split("git when-merged -l "+sha),
            stderr=subprocess.STDOUT, encoding="437").split('\n')
        dateline=None
        direct_commit=False
        for nextLine in lines:
                if bool(re.search('Commit is directly on this branch',nextLine,re.I)):
                        direct_commit=True
                if bool(re.match('Date:', nextLine,re.I)):
                        dateline=nextLine
                        break
        if direct_commit or dateline==None:
                if commit['author_date']>commit['commit_date']:
                        #possible rebase
                        date=commit['author_date'].strftime("%Y-%m-%d %H:%M:%S")
                else:
                        date=commit['commit_date'].strftime("%Y-%m-%d %H:%M:%S")
        else:
                date= re.match('Date:(.*)',dateline,re.I).group(1)
                date=date.strip()
                date=dp.parse(date)
                date=date.strftime("%Y-%m-%d %H:%M:%S")
        query='insert into merge_date values('+str(id)+',"'+str(date)+'");'
        try:
                execute(query)
        except Exception as e:
                print('synchronized machines',e)
        return date
# first look for file_activity with the main affected file
def main_file_actionability():
        query="select * from alerts where is_invalid=0 and status='Fixed' and stream='"+project+"' \
                        and idalerts not in (select alert_id from actionability) \
                        and idalerts > "+str(start) + " and idalerts <"+str(end)
        print(query)
        all_alerts=execute(query)
        print(len(all_alerts))
        for alert in all_alerts:
                aid=alert["idalerts"]
                # initialize actionability columns with default values
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

                first_detected_date=alert['first_detected'].strftime("%Y-%m-%d")

                last_snapshot=str(alert["last_snapshot_id"])
                # get last detected dates
                query="select * from snapshots where idsnapshots="+last_snapshot+" and stream='" +project +"';"
                temp=execute(query)[0]
                if temp['code_version_date']!=None:
                        last_detected_date=temp['code_version_date']
                else:
                        last_detected_date=temp["date"]
                last_detected_date=last_detected_date.strftime("%Y-%m-%d") +" 00:00:00" #to maintain start of the day
                query="select * from snapshots where last_snapshot="+last_snapshot+" and stream='" +project +"';"
                temp=execute(query)[0]
                if temp['code_version_date']!=None:
                        first_not_detected_anymore_date=temp['code_version_date']
                else:
                        first_not_detected_anymore_date=temp["date"]
                first_not_detected_anymore_date=first_not_detected_anymore_date.strftime("%Y-%m-%d") +" 23:59:59" #to maintain end of the day

                
                fid=alert["file_id"]
                # look at if there's a commit (both author and commit date) within 
                # first_detected and first_not_detected
                query='''select * from filecommits fc join commits c on fc.commit_id=c.idcommits 
                        join files f on f.idfiles=fc.file_id
                        where
                        fc.file_id= ''' + str(fid) + ''' and ((c.commit_date >="''' +first_detected_date+ \
                        '''" and c.commit_date <="''' +first_not_detected_anymore_date +'''")
                        or (c.author_date >="''' +first_detected_date+ \
                        '''" and c.author_date <="''' +first_not_detected_anymore_date +'''"))
                        ;'''
                #sanity check by mining git again?
                results=execute(query)
                merged_commits=[]
                if len(results)>0:
                        # for each commit also get the merged date
                        for item in results:
                                merge_date=get_merged_date(item['idcommits'],item['sha'])
                                item['merge_date']=merge_date
                                if merge_date>=last_detected_date and merge_date<=first_not_detected_anymore_date:
                                        merged_commits.append(item)
                results=merged_commits #need to refactor this
                if len(results)>0:
                        file_activity_around_fix='yes'

                        # check if the file is deleted or renamed (involved moved) in the last commit
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
                                        # look for suppression keywords in commit diff
                                        suppression_word=search_suppression_keywords_in_commit_diffs(c['sha'],c['filepath'])
                                        if suppression_word!=None:
                                                suppression='yes'
                                                suppress_commit=str(c['commit_id'])
                                                suppress_keyword=suppression_word
                                                break
                                if suppress_commit==None:
                                        # developer fix
                                        if len(commits)==1:
                                                single_fix_commit=str(commits[0]['commit_id'])
                                        else:
                                                # look for keyword coverity, CID
                                                temp=[]
                                                for c in commits:
                                                        temp.append(str(c['commit_id']))
                                                        if (bool(re.search('coverity',c['msg'],re.I))) or (bool(re.search('CID[\s0-9]',c['msg'],re.I))):
                                                                single_fix_commit=str(c['commit_id'])
                                                fix_commits=','.join(temp)
                        
                # determine actionability
                if marked_bug=='yes' or single_fix_commit!=None or fix_commits!=None:
                        actionability=1
                # print((str(aid),actionability,marked_bug,file_activity_around_fix,single_fix_commit,fix_commits,deleted, 
                #         delete_commit,renamed,rename_commit,transfered_alert_id,suppression,suppress_commit,suppress_keyword))
                try:
                        with connection.cursor() as cursor:
                                cursor.execute('insert into actionability values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', 
                                (str(aid),actionability,marked_bug,file_activity_around_fix,single_fix_commit,fix_commits,deleted, 
                                delete_commit,renamed,rename_commit,transfered_alert_id,suppression,suppress_commit,suppress_keyword))
                                print(str(aid))
                except Exception as e:
                        print("hello",e)







# get alerts with no event history and make a temporary table for them 
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
                # get last detected dates
                query="select date from snapshots where idsnapshots="+last_snapshot+" and stream='" +project +"';"
                last_detected_date=execute(query)[0]["date"]
                last_detected_date=last_detected_date.strftime("%Y-%m-%d") + " 00:00:00"
                query="select date from snapshots where last_snapshot="+last_snapshot+" and stream='" +project +"';"
                first_not_detected_anymore_date=execute(query)[0]["date"]
                first_not_detected_anymore_date=first_not_detected_anymore_date.strftime("%Y-%m-%d") + " 00:00:00"

                for fid in locations.keys():
                        # look at if there's a commit within above two dates
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
                and a.is_invalid=0
                and a.classification="Bug"
                and a.stream="''' + project + '"'
        results=execute(query)
        temp=[]
        for item in results:
                temp.append(item['diff'])
        
        bug_lifespan=np.median(temp)
        f.write("median lifspan of  marked bug are : "+str(bug_lifespan)+'\n')

       # 3 is for other-file alerts  
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
        query='''select a.idalerts,a.cid, b.*,f.filepath_on_coverity, ac.*, datediff(s.date,a.first_detected) as diff
                from actionability ac
                join alerts a
                on a.idalerts=ac.alert_id 
                join files f
                on f.idfiles=a.file_id
                join bug_types b
                on b.idbug_types=a.bug_type
                join snapshots s
                on a.last_snapshot_id=s.idsnapshots
                where ac.actionability=1
                and (ac.single_fix_commit is not null or ac.fix_commits is not null)
                and a.stream="'''+project+'''"
                order by rand()
                limit 50'''
        results=execute(query)

        row=2
        for item in results:
                # get commit hashes
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
                        ws1['D'+str(row)]=item['impact']
                        ws1['E'+str(row)]=item['filepath_on_coverity']
                        # look at lifespan
                        ws1['F'+str(row)]=item['diff']
                        # complexity I can check on the commit diffs itself
                        ws1['G'+str(row)]=c['sha']
                        # if len(commits)>1:
                        #         ws1['H'+str(row)]="\\b"+c['message'].encode('ascii','ignore')+"\\b0"
                        # else:
                        ws1['H'+str(row)]=c['message'].encode('ascii','ignore').decode()
                        row+=1

        ws2=wb.create_sheet("Unactionable Alerts",1)

        query='''select a.idalerts,a.cid, b.*, f.filepath_on_coverity, s.date as lastdate, ac.*
                from actionability ac
                join alerts a
                on a.idalerts=ac.alert_id 
                join files f
                on f.idfiles=a.file_id
                join bug_types b
                on b.idbug_types=a.bug_type
                join snapshots s
                on a.last_snapshot_id=s.idsnapshots
                where ac.actionability=0
                and (ac.file_deleted is null and ac.file_renamed is null)
                and a.stream="'''+project+'''"
                order by rand()
                limit 50'''
        results=execute(query)

        row=2
        for item in results:
                ws2['A'+str(row)]=item['idalerts']
                ws2['B'+str(row)]=item['cid']
                ws2['C'+str(row)]=item['type']
                ws2['D'+str(row)]=item['impact']
                ws2['E'+str(row)]= item['lastdate']
                ws2['F'+str(row)]=item['filepath_on_coverity']
                ws2['G'+str(row)]=item['file_deleted']
                ws2['H'+str(row)]=item['file_renamed']
                ws2['I'+str(row)]=item['suppression']
                ws2['J'+str(row)]='*'
                row+=1
        
        ws3=wb.create_sheet("Single Fix Commits",2)
        query='''select a.idalerts,a.cid, b.*, f.filepath_on_coverity, ac.*, datediff(s.date,a.first_detected) as diff
                from actionability ac
                join alerts a
                on a.idalerts=ac.alert_id 
                join files f
                on f.idfiles=a.file_id
                join bug_types b
                on b.idbug_types=a.bug_type
                join snapshots s
                on a.last_snapshot_id=s.idsnapshots
                where ac.actionability=1
                and ac.single_fix_commit is not null
                and a.stream="'''+project+'''"
                order by rand()
                limit 50'''
        results=execute(query)

        row=2
        for item in results:
                # get commit hashes
                commits=[]
                if item['single_fix_commit']!=None:
                        query="select * from commits c\
                                join merge_date m on c.idcommits=m.merge_date \
                                where idcommits="+str(item['single_fix_commit'])
                        commits.append(execute(query)[0])
                for c in commits:   
                        ws3['A'+str(row)]=item['idalerts']
                        ws3['B'+str(row)]=item['cid']
                        ws3['C'+str(row)]=item['type']
                        ws3['D'+str(row)]=item['impact']
                        ws3['E'+str(row)]=item['filepath_on_coverity']
                        # look at lifespan
                        ws3['F'+str(row)]=item['diff']
                        # complexity I can check on the commit diffs itself
                        ws3['G'+str(row)]=c['sha']
                        ws3['H'+str(row)]=c['message'].encode('ascii',errors='ignore').decode()
                        ws3['I'+str(row)]=c['merge_date']
                        row+=1

        wb.save('Project_'+project+'.xlsx')
def is_number(n):
    try:
        int(n)
    except ValueError:
        return False
    return True
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
        #Need to change this
        # we search this only for fixed alerts as
        # alerts are supposed to be eliminated 
        # when the file is renamed (deleted)
        query='''select count(*) as c
                from alerts
                where stream= "''' +project+'''"
                and idalerts in
                (select alert_id from actionability 
                where file_renamed="yes")''' 
        c=execute(query)[0]['c']
        f.write('the number of alerts that are invalidated due to file renaming is: '+str(c)+'\n')

        query='''select count(*) as c
                from alerts
                where stream= "''' +project+'''"
                and idalerts in
                (select alert_id from actionability 
                where file_renamed="yes"
                and transfered_alert_id is not null)''' 
        c=execute(query)[0]['c']
        f.write('the number of alerts that are transfered due to file renaming is: '+str(c)+'\n')

def patch_complexity():
        # revoking this function
        query='''select count(*) as c
                from actionability ac
                join alerts a 
                on a.idalerts=ac.alert_id
                where a.stream="'''+project +'''"
                and a.is_invalid=0
                and ac.single_fix_commit is not null'''
        fix_commit_tracked=execute(query)[0]['c']
        f.write("fix commit tracked for alerts: "+str(fix_commit_tracked)+'\n')

        

        query='''select fc.*
                from alerts a
                join actionability ac
                on a.idalerts=ac.alert_id
                join fix_complexity fc
                on fc.alert_id=ac.alert_id
                and fc.commit_id=ac.single_fix_commit
                where a.stream="'''+project+'''"
                and a.status='Fixed'
                and a.is_invalid=0
                and ac.single_fix_commit is not null;'''
        results=execute(query)
        files=[]
        net_loc=[]
        net_logical=[]
        in_loc=[]
        in_logical=[]
        for item in results:
                file_count=float(item['file_count'])/float(item['total_fixed_alerts'])
                loc_change=float(item['net_loc_change'])/float(item['total_fixed_alerts'])
                logical_change=float(item['net_logical_change'])/(item['total_fixed_alerts'])
                files.append(file_count)
                net_loc.append(loc_change)
                net_logical.append(logical_change)
                loc_change=float(item['infile_loc_change'])/float(item['infile_fixed_alerts'])
                logical_change=float(item['infile_logical_change'])/(item['infile_fixed_alerts'])
                in_loc.append(loc_change)
                in_logical.append(logical_change)
        f.write("median affected files: "+str(np.median(files))+'\n')
        f.write("median net LOC change: "+str(np.median(net_loc))+'\n')
        f.write("median net logical change: "+str(np.median(net_logical))+'\n')
        f.write("median infile LOC change: "+str(np.median(in_loc))+'\n')
        f.write("median infile logical change: "+str(np.median(in_logical))+'\n')
        # query='''select * from
        # (select ac.single_fix_commit, a.file_id, count(*)  as c
        # from actionability ac
        # join alerts a
        # on ac.alert_id=a.idalerts 
        # where a.stream="'''+project+'''"
        # and ac.single_fix_commit is not null
        # and a.is_invalid=0
        # group by ac.single_fix_commit,a.file_id) as fix
        # join filecommits fc
        # on fix.single_fix_commit=fc.commit_id'''
        # results=execute(query)
        # loc=[]
        # for item in results:
        #         if item['lines_added']==None or item['lines_removed']==None:
        #                 continue
        #         c=item['c']
        #         l=float(item['lines_added']+item['lines_removed'])
        #         loc.append(l/c)
        # loc.sort()
        # f.write("median in-file LOC change: "+str(np.median(loc)))

def methodology_infos():
        get_general_report()
        # need to give info on data cleaning
        file_renaming_info()

def update_fix_commit_infos():
        query='''select distinct ac.single_fix_commit, c.*,f.*,a.idalerts from actionability ac
                join alerts a
                on ac.alert_id=a.idalerts
                join commits c
                on c.idcommits = ac.single_fix_commit
                join files f
                on f.idfiles=a.file_id
                where ac.single_fix_commit is not null
                and ac.actionability=1
                and a.is_invalid=0
                and a.status='Fixed'
                and a.stream ="'''+project+'"'
        results=execute(query)

        for item in results:
                sha=item['sha']
                cid=item['idcommits']
                filepath=item['filepath_on_coverity'][1:]
                fid=item['idfiles']
                aid=item['idalerts']
                arguments=process_commit(sha,filepath)

                query='select count(*) as c from actionability where single_fix_commit='+str(cid)
                total_fixed_alerts=execute(query)[0]['c']
                arguments.append(total_fixed_alerts)

                query='''select count(*) as c from actionability ac
                        join alerts a
                        on a.idalerts = ac.alert_id
                        where ac.single_fix_commit='''+str(cid)+'''
                        and a.file_id='''+str(fid)
                infile_fixed_alerts=execute(query)[0]['c']
                arguments.append(infile_fixed_alerts)

                query="insert into fix_complexity values("+str(cid)+","+str(aid)+","
                for idx, arg in enumerate(arguments):
                    # value cleaning
                    arg=str(arg) #if not string
                    arg=arg.strip() #if any whitespace ahead or trailing
                    # remove illegal character
                    arg=arg.replace('"',"'")

                    if is_number(arg) or arg=="null":
                        query+=arg
                    else:
                        query+='"'+arg+'"'
                    if idx<len(arguments)-1:
                        query+=","
                query+=");"
                with connection.cursor() as cursor:
                    try:
                        cursor.execute(query)
                    except Exception as e:
                        print(e,query)
        # for item in results:
        #         d={}
        #         sha=item['sha']
        #         cid=item['idcommits']
        #         filepath=item['filepath_on_coverity'][1:]
        #         fid=item['idfiles']
        #         lines=subprocess.check_output(
        #                 shlex.split('git show --stat '+sha),
        #                 encoding="437"
        #         ).split('\n')
        #         line=lines[-2].strip()
        #         temp=line.split(',')
        #         info=[]
        #         query=''
        #         if len(temp)==3:
        #                 for t in temp:
        #                         t=t.strip()
        #                         info.append(t.split(' ')[0])
        #                 #update commit table
        #                 query='update commits set affected_files_count='+info[0]+',net_lines_added='+info[1]+',net_lines_removed='+info[2]+' where idcommits='+str(cid)
        #         elif len(temp)==2:
        #                 if 'insert' in line:
        #                         for t in temp:
        #                                 t=t.strip()
        #                                 info.append(t.split(' ')[0])
        #                         #update commit table
        #                         query='update commits set affected_files_count='+info[0]+',net_lines_added='+info[1]+',net_lines_removed=0 where idcommits='+str(cid)
        #                 elif 'delet' in line:
        #                         for t in temp:
        #                                 t=t.strip()
        #                                 info.append(t.split(' ')[0])
        #                         #update commit table
        #                         query='update commits set affected_files_count='+info[0]+',net_lines_added=0,net_lines_removed='+info[1]+' where idcommits='+str(cid)
        #         execute(query)  



def lifespan_vs_complexity():
        query='''select idalerts, datediff(s.date,a.first_detected) as diff from actionability ac
                join alerts a 
                on a.idalerts=ac.alert_id
                join snapshots s
                on a.last_snapshot_id=s.idsnapshots
                where ac.actionability = 1
                and a.stream="''' + project + '"'

def remove_blank_lines_and_comments(diff):
        diff=re.sub('/\\*(.|\n)*\\*/','',diff) # remmoving multiline comments
        lines=diff.split('\n')
        copy=[]
        for line in lines:
                line=re.sub('//(.*)','',line) #removing single line comments
                line=line.strip() #stripping trailing whitespaces
                if not (line=='' or line=='\n'):
                        # however changes will start with + or -
                        if line.startswith('+') or line.startswith('-'):
                                temp=line[1:] #take the actual line
                                temp=temp.strip() #stripping trailing whitespaces
                                if not (temp=='' or temp=='\n'):
                                        copy.append(line)
                        else:
                                copy.append(line)
        return '\n'.join(copy)
def process_commit(sha,filepath):
        affected_files=0
        net_loc_change=0
        infile_loc_change=0
        net_logical_change=0
        infile_logical_change=0
        full=subprocess.check_output(
                shlex.split("git show "+sha),
                encoding="437"
        )
        t=open('temp.txt','w')
        t.write(full)
        t.close()

        diffs=full.split('diff --git ')
        del diffs[0]
        affected_files=len(diffs)

        for diff in diffs:
                loc=0
                logical=0
                diff=re.sub('[@]{3,}','',diff)
                parts=diff.split('@@')
                del parts[0]
                ind = 1
                while ind < len(parts):
                        cur_diff=parts[ind]
                        cur_diff=remove_blank_lines_and_comments(cur_diff)
                        lines=cur_diff.split('\n')
                        flag=False #flag to keep track of logical changes
                        for line in lines:
                                if line.startswith('+') or line.startswith('-'):
                                        loc+=1
                                        if not flag:
                                                logical+=1
                                                flag=True
                                else:
                                        flag=False
                        ind+=2
                if filepath in diff:
                       infile_loc_change=loc
                       infile_logical_change=logical
                net_loc_change+=loc
                net_logical_change+=logical
        
        return [affected_files,net_loc_change,infile_loc_change,net_logical_change,infile_logical_change]

                        


        pass
if __name__ == "__main__":
        #alerts_from_other_files()
        main_file_actionability()
        # invalidate_file_renamed_alerts()
        
        
        # # # reporting functions
        # methodology_infos()
        # get_alert_infos()
        # actionability_and_lifespan_report()
        
        # update_fix_commit_infos()
        # patch_complexity()
        #manual_validation_file()

        f.close()
