import os
import sys
sys.path.append('../../main')
import shlex
import subprocess
import json
import requests
import sql
import common
import patch2coverity as pc
import time
from multiprocessing import Pool

projectId = 7
'''
Get the memory related Linux CVEs
    1) Check if it's within Linux kernel or external product
        check cpes what product it contains: checking cpes is not reliable. even linux kernel ones can have other project listed.
        Checking "Linux Kernel" in summary is a good indicator? - we can just use this and validate the rest of them by spot check
    
    2) check commits -
        either in https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/eoan/commit/?id=5df147c8140efc71ac0879ae3b0057f577226d4c
        or https://github.com/torvalds/linux/commit/c4c07b4d6fa1f11880eab8e076d3d060ef3f55fc
        
        commit/?id=5df147c8140efc71ac0879ae3b0057f577226d4c or commit/c4c07b4d6fa1f11880eab8e076d3d060ef3f55fc
        then check with git show if it's a valid commit
'''


def get_cve_data(cve):
    url = 'https://services.nvd.nist.gov/rest/json/cve/1.0/'+cve
    response = requests.get(url)
    while response.status_code != 200:
        time.sleep(1)
        response = requests.get(url)
    print('fetched cve: ', cve)

    data = json.loads(response.content)
    data = data['result']['CVE_Items'][0]

    return data


def get_cves():
    'get memory related cves from Linux'
    q = '''select distinct  c.id
         from cve c
        join memory_cwe mc on c.CWE = mc.CWE
        where memory=1
        and project_id=%s
        and id not in
        (select cve from cve_fix_commits)'''
    return sql.execute(q, (projectId,))


def parse_commit(url):
    assert 'commit' in url 

    if 'id=' in url:
        commit = url.split('id=')[-1]
    else:
        commit = url.split('/')[-1]
        
    return commit


def validate_commit(commit, projectd=projectId):
    common.switch_dir_to_project_path(projectId)
    try:
        output = subprocess.check_output(
                shlex.split('git show '+commit), 
                stderr=subprocess.STDOUT,
                encoding="437")
        if 'commit {}'.format(commit) in output:
            return True
        return False
    except: 
        return False

def collect_commit(item):
    conn=sql.create_db_connection()
    cve = item['id']
    data = get_cve_data(cve)
    refs = data['cve']['references']['reference_data']
    commits = []
    for ref in refs:
        url = ref['url']
        if 'commit/' in url:
            commits.append(parse_commit(url))
    commits = list(set(commits))
    valid_commits=[]
    for commit in commits:
        if validate_commit(commit):
            valid_commits.append(commit)
    insert_cve_fix_commits(cve,valid_commits,connection=conn)
    print("inserted ", cve)
        
    

def get_publish_date(cve):
    return sql.execute('select publish_date from cve where id=%s',(cve,))[0]['publish_date']

def analyze(cves):
    for cve in cves.keys():
        try:
            publishDate = get_publish_date(cve)
            commits=cves[cve]
            files, functions = pc.get_file_function_names(projectId, commits)
            fileAlerts= pc.get_alert_on_files(publishDate, files)
            if fileAlerts:
                for alert in fileAlerts:
                    alertId=alert['id']
                    sql.execute('insert into cve_file_alerts values(%s,%s)',(cve,alertId))
                
                functionAlerts=[]
                for file in functions.keys():
                    for func in functions[file]:
                            functionAlerts += pc.get_alert_on_functions(publishDate, file, func)
                
                for alert in functionAlerts:
                    alertId=alert['id']
                    sql.execute('insert into cve_function_alerts values(%s,%s)',(cve,alertId))
            else:
                sql.execute('insert into cve_file_alerts values(%s,%s)',(cve,0))
        except:
            sql.execute('insert into cve_file_alerts values(%s,%s)',(cve,-1))
        print('analyzed',cve)
def insert_cve_fix_commits(cve,commits,connection=None):
    q='insert into cve_fix_commits values(%s,%s)'
    if not commits:
        sql.execute(q,(cve,None),connection=connection)
        return
    for commit in commits:
        sql.execute(q,(cve,commit),connection=connection)

if __name__ == '__main__':
    # cves = get_cves()
    # pool=Pool(os.cpu_count())
    # pool.map(collect_commit, cves)
    
    results = sql.execute('select * from cve_fix_commits where commit is not null')
    cves={}
    for item in results:
        id=item['cve']
        commit=item['commit']
        if id not in cves:
            cves[id]=[commit]
        else:
            cves[id].append(commit)
    print(len(list(cves.keys())))
    analyze(cves)
