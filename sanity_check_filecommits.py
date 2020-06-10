'''check if files got all their commits in filecommits,
do with firefox and linux once again?'''
import pymysql
import sys
import datetime
import re
import os
import subprocess
import re
import shlex
import dateutil.parser as dp
import add_commits as ac

#read command line arguments
project=sys.argv[1]
path="/Users/nasifimtiaz/Desktop/new_data/"+sys.argv[2]
start=sys.argv[3]
end=sys.argv[4]
os.chdir(path)




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

def get_all_files(project):
#Linux starting from 31052
    with connection.cursor() as cursor:
        query='''select distinct f.idfiles, f.filepath_on_coverity
                from alerts a
                join files f
                on a.file_id=f.idfiles
                where a.stream="''' + str(project) + \
                '''" and a.is_invalid=0 and a.status='Fixed'
                and f.idfiles > ''' + str(start)+ \
                " and f.idfiles <= "+str(end)
        if project=='Firefox':
            query+= ''' and not (f.filepath_on_coverity  like '/obj-x86_64-pc-linux-gnu%'
                    or f.filepath_on_coverity  like '/usr%'
                    or f.filepath_on_coverity like '/rdf%'
                    or f.filepath_on_coverity  like '/embedding%'
                    or f.filepath_on_coverity  like '/obj-x86_64-unknown-linux-gnu%'
                    or f.filepath_on_coverity  like '/obj-coverity%'
                    or f.filepath_on_coverity  like '/content%'
                    or f.filepath_on_coverity  like '/webapprt%'
                    or f.filepath_on_coverity  like '/jpeg%'
                    or f.filepath_on_coverity  like '/home/scan%'
                    or f.filepath_on_coverity  like '/dbm%'
                    or f.filepath_on_coverity  like '/xpinstall%'
                    or f.filepath_on_coverity  like '/obj%'
                    or f.filepath_on_coverity  like '/directory%'
                    or f.filepath_on_coverity  like '/mailnews%')'''
        #query="select * from files where project='"+str(project)+"' and idfiles >" + str(last_checked)+";"
        print(query)
        cursor.execute(query)
        results=cursor.fetchall()
        return results
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
def get_commit_count_from_git(filepath):
    temp=get_start_end_date()
    start_date=temp['start_date']
    end_date= temp['end_date']
    lines=subprocess.check_output(
        shlex.split("git log --follow --oneline --after='"+ start_date +"' --before='"+ end_date+"' -- "+filepath),
        stderr=subprocess.STDOUT,
        encoding='437'
    ).split('\n')
    return len(lines) - 1 

def get_commit_count_from_db(file_id):
    query='''select count(*) as c
            from filecommits 
            where file_id='''+str(file_id)
    return int(execute(query)[0]['c'])

if __name__ == "__main__":
    #check if project exists
    if not ac.project_exists(project):
        print("project does not exist")
        exit()
    # get all the files from database
    files=get_all_files(project)
    #files.reverse()
    print(len(files))
    for f in files:
        #get fid and see if it is already covered

        #parse local filepath
        path=f["filepath_on_coverity"]
        path=path[1:] #cut the beginning slash
        print(path)
        file_id=f["idfiles"]
        db=get_commit_count_from_db(file_id)
        git = get_commit_count_from_git(path)
        print(db,git)
        if db<git:
            print("need to recheck")
            #do add commits again
            commits=ac.mine_gitlog(path)
            print(len(commits))
            for commit in commits:
                sha=commit["hash"]
                if ac.commitId_ifExists(sha)==None:
                    ac.add_commit(commit) #not adding affected files count, lines added, and removed for now
                commit_id=ac.commitId_ifExists(sha)   
                if ac.filecommitId_ifExists(file_id,commit_id)==None:
                    ac.add_filecommits(file_id,path,commit_id,commit)
                filecommit_id = ac.filecommitId_ifExists(file_id,commit_id)
        print(file_id)
    print("script ended")