import pymysql
import os
import sys
import subprocess
import shlex
import re
import dateutil.parser as dp



project=str(sys.argv[1])
path="/Users/nasifimtiaz/Desktop/new_data/"+sys.argv[2]
start=sys.argv[3]
end=sys.argv[4]
os.chdir(path)

def get_start_end_date():
    d={}
    with connection.cursor() as cursor:
        query="select start_date, end_date from projects where name='" + project + "';"
        cursor.execute(query)
        result=cursor.fetchone()
        start=result['start_date']
        end=result['end_date']
        start=start.strftime('%Y-%m-%d')
        d['start_date']=start
        end=end.strftime('%Y-%m-%d')
        d['end_date']=end
        return d


#open sql connection 
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='soverityscan_sandbox',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)
temp=get_start_end_date()
start_date=temp['start_date']
end_date= temp['end_date']
def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results=cursor.fetchall()
    return results

query='''select * from commits c
        join filecommits fc
        on c.idcommits=fc.commit_id
        join alerts a
        on a.file_id=fc.file_id
        where project="'''+project+'''"
        and (commit_date >= "'''+start_date+ '''" or author_date >="'''+start_date+ '''")
        and (commit_date <= "'''+end_date+ '''" or author_date <="'''+end_date+ '''")
        and merge_date is null
        and is_invalid=0 and status='Fixed'
        and idcommits > '''+str(start)+" and idcommits <="+str(end)
commits=execute(query)
print(query)
print(len(commits))
print(commits[0]['idcommits'],commits[-1]['idcommits'])
for commit in commits:
    id=commit['idcommits']
    sha=commit['sha']
    lines=subprocess.check_output(
            shlex.split("git when-merged -l "+sha), 
            stderr=subprocess.STDOUT,encoding="437").split('\n')
    dateline=None
    direct_commit=False
    for nextLine in lines:
        if bool(re.search('Commit is directly on this branch',nextLine,re.I)):
            direct_commit=True
        if bool(re.match('Date:', nextLine,re.I)):
            dateline=nextLine
            break
    if direct_commit or dateline==None:
        date="1111-11-11 11:11:11"
        # if commit['author_date']<commit['commit_date']:
        #     date=commit['author_date']
        # else:
        #     date=commit['commit_date']
    else:
        date= re.match('Date:(.*)',dateline,re.I).group(1)
        date=date.strip()
        date=dp.parse(date)
        date=date.strftime("%Y-%m-%d %H:%M:%S")
    query='update commits set merge_date="'+date+'" where idcommits='+str(id)
    execute(query)
    print(query)
