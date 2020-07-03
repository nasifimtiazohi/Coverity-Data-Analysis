import common, sql
import os, sys, time
import add_project_snapshots as aps
import add_alerts as aa
import filename_corrections as fc
import add_commits as ac
import detect_external_file as ef
import determine_actionability as act
import patch_complexity as pc

add_new_project_queries={
    #initiate Chaos control framework
    '!CHAOS Control System' : '''insert into project values(null,'!CHAOS Control System','https://github.com/bisegni/chaosframework.git',
    'https://github.com/bisegni/chaosframework.git','master',null,null)''',
    'Chromium EC': '''insert into project values(null,'Chromium EC','https://chromium.googlesource.com/chromiumos/platform/ec',
    'https://chromium.googlesource.com/chromiumos/platform/ec','master',null,null)''',
    'OpenCV':'''insert into project values(null,'OpenCV','https://github.com/opencv/opencv',
    'https://github.com/opencv/opencv','master',null,null)''',
    'LibreOffice':'''insert into project values(null,'LibreOffice','https://cgit.freedesktop.org/libreoffice/core',
    'https://cgit.freedesktop.org/libreoffice/core','master',null,null)''',
    'Thunderbird':'''insert into project values(null,'Thunderbird','http://hg.mozilla.org/comm-central/',
    'https://github.com/mozilla/releases-comm-central','master',null,null)''',
    'VTK':'''insert into project values(null,'VTK','https://gitlab.kitware.com/vtk/vtk.git',
    'https://gitlab.kitware.com/vtk/vtk.git','master',null,null)'''
}

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
                                (select start_date 
                                from project 
                                where id=%s)'''
    sql.execute(q,(projectId,projectId))

def identify_outlier_spikes(projectId):
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
    os.system('git pull')
    logging.info("waiting 5 seconds")
    time.sleep(5)

if __name__=='__main__':
    project, snapshotFile, alertFile = read_cl_args()
    projectId=common.get_project_id(project)
    
    if not projectId:
        #new project found
        #insert project
        sql.execute(add_new_project_queries[project])
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
    set_start_and_end_date(projectId)
    fc.resolve_filename_prefixes(projectId)
    ac.mine_commits(projectId)
    ef.handle_external_files(projectId) #invalidates external file alerts
    act.analyze_actionability(projectId) #invalidate file renames/deletes
    pc.update_fix_complexity(projectId)

    