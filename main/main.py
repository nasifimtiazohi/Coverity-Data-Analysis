import common, sql
import os, sys, time
import add_project_snapshots as aps
import add_alerts as aa
import filename_corrections as fc
import add_commits as ac
import detect_external_file as ef
import determine_actionability as act
import patch_complexity as pc
import subprocess, shlex


def read_cl_args():
    return sys.argv[1], sys.argv[2], sys.argv[3]

def set_start_and_end_date(projectId):
    q='''select date from snapshot
            where project_id=%s
            order by date asc;'''
    results=sql.execute(q,(projectId,))
    start_date=results[0]['date']
    end_date=results[-1]['date']
    q=''' update project
            set start_date=%s, end_date=%s
            where id=%s '''
    sql.execute(q,(start_date,end_date,projectId))

def invalidate_alerts_before_start_date(projectId):
    q = ''' update alert
        set is_invalid=1 
        where project_id= %s and first_detected  < 
                                (select DATE_FORMAT(start_date,'%Y-%m-%d') 
                                from project 
                                where id=%s)'''
    sql.execute(q,(projectId,projectId))

def identify_outlier_spikes(projectId):
    ''' manual approach'''
    threshold=1000
    q='''select project_id, type, first_detected, last_snapshot_id, count(*) as c
        from alert a
        join alert_type t on a.alert_type_id = t.id
        where project_id=%s
        group by project_id, alert_type_id, first_detected, last_snapshot_id
        order by count(*) desc;'''
    results=sql.execute(q,(projectId,))
    i=0
    while i<len(results):
        if results[i]['c'] < threshold:
            break
        
        i+=1
    return results[:i]

def initial_cleaning():
    #do initial data cleaning
    ## before start date
    invalidate_alerts_before_start_date(projectId)
    ## outlier spikes
    suspects = identify_outlier_spikes(projectId)
    if suspects:
        print(suspects)
    print(fc.get_base_names(fc.get_all_files(projectId)))
    #manually inspect here, outliers and filenames
    exit()

def git_pull(projectId):
    common.switch_dir_to_project_path(projectId)
    lines = subprocess.check_output(
            shlex.split('git pull'), 
            stderr=subprocess.STDOUT,
            encoding="437"
            ).split('\n')
    print(lines)
    

def is_valid_git_remote(url):
    lines = subprocess.check_output(
            shlex.split('git ls-remote {}'.format(url)), 
            stderr=subprocess.STDOUT,
            encoding="437"
            )
    if 'fatal: Could not read from remote repository' in lines:
        return False
    assert 'HEAD' in lines
    return True

def ask_project_parameters(project):
    print("Project does not exist in database. Please provide below information to add to dataset.")
    print("Enter the git remote url for the project: ")
    git_url=input()
    while not is_valid_git_remote(git_url):
        print("Invalid remote url. Enter correct https git remote url for the project: ")
        git_url=input()
    
    print("Enter the github url for the project: ")
    gh_url=input()
    print("Enter the brance name")
    branch = input()
    
    q='insert into project values(null,%s,%s,%s,%s,null,null)'
    sql.execute(q,(project, git_url, gh_url, branch))
    

if __name__=='__main__':
    project, snapshotFile, alertFile = read_cl_args()
    projectId=common.get_project_id(project)
    
    if not projectId:
        ask_project_parameters(project)
        projectId=common.get_project_id(project)
        aps.add_snapshots(snapshotFile)
        aa.add_n_update_alerts(projectId, alertFile)
        set_start_and_end_date(projectId)
        #do initial data cleaning
        ## before start date
        invalidate_alerts_before_start_date(projectId)
        ## outlier spikes
        suspects = identify_outlier_spikes(projectId)
        if suspects:
            print(suspects)
        print(fc.get_base_names(fc.get_all_files(projectId)))
        #manually inspect here, outliers and filenames
        exit()
    
    git_pull(projectId)
    aps.add_snapshots(snapshotFile)
    aa.add_n_update_alerts(projectId, alertFile)
    fc.resolve_filename_prefixes(projectId)
    ac.mine_commits(projectId)
    ef.handle_external_files(projectId) #invalidates external file alerts
    act.analyze_actionability(projectId) #invalidate file renames/deletes
    pc.update_fix_complexity(projectId)

    