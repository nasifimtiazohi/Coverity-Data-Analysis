import pymysql
import numpy as np
import re
#open sql connection 
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)
def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()
    return results
def fix_actionability_table():
    query='''select * from actionability_fixed
            where single_fix_commit is not null
            and fix_commits is not null;'''
    results=execute(query)
    for item in results:
        commits=item['fix_commits']
        fix_commits=commits
        single_fix_commit=item['single_fix_commit']
        commits=commits.split(',')
        commits_with_keywords=0
        for c in commits:
            query='select message from commits where idcommits='+c
            msg=execute(query)[0]['message']
            if (bool(re.search('coverity',msg,re.I))) or (bool(re.search('CID[\s0-9]',msg,re.I))):
                commits_with_keywords+=1
        if commits_with_keywords > 1:
            print('yes')
            query='''update actionability_fixed set single_fix_commit = Null where single_fix_commit={}
                        and fix_commits="{}"'''.format(single_fix_commit,fix_commits)
            execute(query)
        else:
            print('no')

def fix_fix_complexity_table():
    query='''select * from actionability
            where single_fix_commit is not null
            and fix_commits is not null;'''
    results=execute(query)
    for item in results:
        alert_id=item['alert_id']
        commits=item['fix_commits']
        commits=commits.split(',')
        commits_with_keywords=0
        for c in commits:
            query='select message from commits where idcommits='+c
            msg=execute(query)[0]['message']
            if (bool(re.search('coverity',msg,re.I))) or (bool(re.search('CID[\s0-9]',msg,re.I))):
                commits_with_keywords+=1
        if commits_with_keywords > 1:
            print('yes')
            query='''delete from fix_complexity_fixed where alert_id={}'''.format(alert_id)
            execute(query)
        else:
            print('no')

if __name__=='__main__':
    fix_fix_complexity_table()

