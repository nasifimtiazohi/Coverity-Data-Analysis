import pymysql
import datetime
import sys
import pydriller
from git import repo

connection = pymysql.connect(host='localhost',
                             user='root',
                             db='890coverity',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

# #TODO: filter commits only within start date and end date of the project with since(startdate)

def get_startdate(project):
    query= "select start_date from projects where stream='"+project +"';"
    with connection.cursor() as cursor:
        cursor.execute(query)
        result=cursor.fetchall()
        startdate= result[0]["start_date"]
    return startdate

def get_github_url(project):
    query="select github_url from projects where stream='"+project +"';"
    with connection.cursor() as cursor:
        cursor.execute(query)
        result=cursor.fetchall()
        url=result[0]["github_url"]
    return url

def project_exists(project):
    query="select * from projects where stream='"+project +"';"
    with connection.cursor() as cursor:
        cursor.execute(query)
        result=cursor.fetchall()
        if len(result)==1:
            return True
        elif len(result)==0:
            print ("project does not exist in database")
        else:
            print("more than one project found. fatal bug")
    return False


if __name__=="__main__":
    #read command line arguments
    project=sys.argv[1]
    path="/Users/nasifimtiaz/Desktop/new_data/"+sys.argv[2]
    #check if project exists
    if not project_exists(project):
        exit()
    files=['xbmc/cores/VideoPlayer/VideoRenderers/ColorManager.cpp'
    # ,
    #         'xbmc/video/VideoDatabase.cpp'
            ]

    repo=pydriller.RepositoryMining(path,since=get_startdate(project))

    for f in files:
        print(f)
        temp=open("temp.txt","w")
        repo._filepath=f
        for commit in repo.traverse_commits():
            if "Eliminate CServiceBroker::GetSettings(); use CServiceBroker" in commit.msg:
                for m in commit.modifications:
                    t=f.split("/")
                    t=t[-1]
                    print("\n",t,"\n")
                    if t in m.filename:
                        temp.write(commit.msg)
                        temp.write(m.filename)
                        temp.write(m.diff)
        break
                

    

    






    










