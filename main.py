import common, sql
import os, sys
import add_project_snapshots as aps
import add_alerts as aa
import filename_corrections as fc
import add_commits as ac
import detect_external_file as ef
import determine_actionability as act

def read_cl_args():
    return sys.argv[1], sys.argv[2], sys.argv[3]

if __name__=='__main__':
    project, snapshotFile, alertFile = read_cl_args()
    projectId=common.get_project_id(project)

    if not projectId:
        #new project found
        #insert project
        #do initial data cleaning
            ## outlier spikes
            ## before start date
        pass
    
    # aps.add_snapshots(snapshotFile)
    # aa.add_n_update_alerts(projectId, alertFile)
    # fc.resolve_duplicates(projectId)
    # ac.mine_commits(projectId)
    # ef.handle_external_files(projectId)

    act.analyze_actionability(projectId)

    