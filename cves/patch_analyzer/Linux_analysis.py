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
import dateutil.parser as dp
import pytz
import re
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

def fill_cve_file_function_alerts():
    q='''select * from cve_fix_commits where commit is not null
            and cve not in
            (select cve from cve_file_alerts);'''
    results = sql.execute(q)
    cves={}
    for item in results:
        id=item['cve']
        commit=item['commit']
        if id not in cves:
            cves[id]=[commit]
        else:
            cves[id].append(commit)
    print(len(list(cves.keys())))
    for cve in cves.keys():
        try:
            publishDate = get_publish_date(cve)
            commits=cves[cve]
            files, functions = pc.get_file_function_names(projectId, commits)
            fileAlerts= pc.get_alert_on_files(publishDate, files)
            if fileAlerts:
                for alert in fileAlerts:
                    alertId=alert['id']
                    sql.execute('insert into cve_file_alerts values(%s,%s,null)',(cve,alertId))
                
                functionAlerts=[]
                for file in functions.keys():
                    for func in functions[file]:
                            functionAlerts += pc.get_alert_on_functions(publishDate, file, func)
                
                for alert in functionAlerts:
                    alertId=alert['id']
                    sql.execute('insert into cve_function_alerts values(%s,%s,null)',(cve,alertId))
            else:
                sql.execute('insert into cve_file_alerts values(%s,%s,null)',(cve,0))
        except:
            sql.execute('insert into cve_file_alerts values(%s,%s,null)',(cve,-1))
        print('analyzed',cve)
def insert_cve_fix_commits(cve,commits,connection=None):
    q='insert into cve_fix_commits values(%s,%s,%s,%s)'
    if not commits:
        sql.execute(q,(cve,None,None,None),connection=connection)
        return
    for commit in commits:
        commit_date=get_commit_date(commit)
        merge_date=get_merged_date(commit)
        sql.execute(q,(cve,commit,commit_date,merge_date),connection=connection)


def determine_fixed_after_patch():
    q='''select *
        from cve_function_alerts cfa
        join cve_fix_commits cfc on cfa.cve = cfc.cve
        join
            (select a.id, a.status, a.first_detected, s.date as fix_date from alert a
                join snapshot s on a.last_snapshot_id=s.id) t
        on cfa.alert_id=t.id'''
    results = sql.execute(q)
    
    q='update cve_function_alerts set fixed_after_patch = %s where cve = %s and alert_id =%s'
    for item in results:
        cve=item['cve']
        aid=item['alert_id']
        if item['status'] != 'Fixed':
            sql.execute(q,('unfixed',cve,aid))
            continue
        commit_date= get_commit_date(item['commit'])
        fix_date=pytz.utc.localize(item['fix_date']).date()
        detection_date=item['first_detected']
        print(cve, commit_date, fix_date, detection_date)
        if commit_date <= fix_date and commit_date >= detection_date:
            sql.execute(q,('yes',cve,aid))
        else:
            sql.execute(q,('no',cve,aid))
        print(cve)
    

def get_commit_date(commit):
    common.switch_dir_to_project_path(projectId)
    output = subprocess.check_output(
                shlex.split("git show --no-patch --no-notes --pretty='%cd' "+commit), 
                stderr=subprocess.STDOUT,
                encoding="437").strip()
    return dp.parse(output).date()

def get_merged_date(sha, connection=None):
    common.switch_dir_to_project_path(projectId,connection=connection)
    # when-merged tool by default checks for master branch
    # https://github.com/mhagger/git-when-merged
    lines = subprocess.check_output(
        shlex.split("git when-merged -l "+sha),
        stderr=subprocess.STDOUT, encoding="437").split('\n')
    dateline = None
    direct_commit = False
    for nextLine in lines:
        if bool(re.search('Commit is directly on this branch', nextLine, re.I)):
            direct_commit = True
        if bool(re.match('Date:', nextLine, re.I)):
            dateline = nextLine
            break
    if direct_commit or not dateline:
        print("direct commit", sha)
        return get_commit_date(sha)
    else:
        date = re.match('Date:(.*)', dateline, re.I).group(1)
        date = date.strip()
        date = dp.parse(date)
    
    return date


def get_dates_patch_commit():
    q='select * from cve_fix_commits where commit is not null and commit_date is null'
    results = sql.execute(q)
    print(len(results))
    for item in results:
        cve=item['cve']
        commit=item['commit']
        commit_date=get_commit_date(commit)
        merge_date=get_merged_date(commit)
        print(commit_date,merge_date,cve,commit)
        q='update cve_fix_commits set commit_date=%s, merge_date=%s where cve=%s and commit=%s'
        sql.execute(q,(commit_date,merge_date,cve,commit))


def get_cve_merge_date(cve):
    q='''select *
        from cve_fix_commits
        where cve=%s;'''
    results=sql.execute(q,(cve,))
    
    dates=[]
    for item in results:
        dates.append(item['merge_date'].date())
    
    dates=list(set(dates))
    
    return dates
    
def analyze():
    q='''select cfa.*,a.*,s.date as last_detected from cve_file_alerts cfa
        join alert a on cfa.alert_id = a.id
        join snapshot s on a.last_snapshot_id=s.id
        where cfa.alert_id > 0;'''
    alerts=sql.execute(q)
    
    q='update cve_file_alerts set fixed_at_patch=%s where cve=%s and alert_id=%s'
    for alert in alerts:
        cve=alert['cve']
        print(cve)
        aid=alert['alert_id']
        if alert['status'] != 'Fixed':
            sql.execute(q,('notFixed',cve,aid))
            continue
        
        first_detected = alert['first_detected']
        last_detected= alert['last_detected'].date()
        first_not_detected_anymore_date =  (common.get_snapshot_date(
                                    projectId, 
                                    common.get_next_snapshotId(projectId, alert['last_snapshot_id']))).date()
        merge_dates=get_cve_merge_date(cve)
        
        flag = False
        for merge_date in merge_dates:
            if first_detected <= merge_date and (merge_date >= last_detected and merge_date <= first_not_detected_anymore_date):
                flag=True
                break
        if flag:
            sql.execute(q,('yes',cve,aid))
        else:
            sql.execute(q,('no',cve,aid))
        

if __name__ == '__main__':
    # cves = get_cves()
    # pool=Pool(os.cpu_count())
    # pool.map(collect_commit, cves)
    # get_dates_patch_commit()
    
    #fill_cve_file_function_alerts()
    
    analyze()
    
    
    
