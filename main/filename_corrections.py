'''this file contains code
on how I corrected filename prefixes 
for each projects'''

'''
while extending dataset for an existing project,
we assume the correction rules should apply to 
new files found (count of new files should be small)
For new project, we manually build this rules by exploration
and by means achieve 100% accuracy.
'''

import common, sql 
import sys, logging


def get_all_files(projectId):
    q='select * from file where project_id=%s'
    return sql.execute(q,(projectId,))

def get_base_names(files):
    'look at base names when exploring a new project'
    bases=[]
    for file in files:
        fullname=file['filepath_on_coverity']
        temp=fullname.split('/')
        if temp[1] not in bases:
            bases.append(temp[1])
    return bases

temp=[]
a=[]
hm={'Samba':['/samba','/bin/default','/base/src'],
    'Kodi':['/home/jenkins/workspace/LINUX-64-soverityscan_sandbox'],
    'Linux':['/linux'],
    'Firefox':['/mozilla','/base/src/mozilla'],
    'Chromium EC':['/build/krane','/build/kukui'],
    'OpenCV':['/home/build/opencv','/home/opencv/opencv_src','/home/vrabaud/software/opencv',
              '/home/vrabaud/software/opencv_trunk','/java_test/src/org/opencv','/src/org/opencv',
              '/_trunk'],
    'LibreOffice':['/workdir',
            '/workdir/CustomTarget',
            '/workdir/LexTarget',
            '/workdir/UnoApiHeadersTarget',
            '/workdir/UnpackedTarball',
            '/workdir/YaccTarget',
            '/workdir/unxlngx6.pro/CustomTarget',
            '/workdir/unxlngx6.pro/LexTarget',
            '/workdir/unxlngx6.pro/UnoApiHeadersTarget',
            '/workdir/unxlngx6.pro/UnpackedTarball',
            '/workdir/unxlngx6.pro/YaccTarget',
            '/CustomTarget',
            '/LexTarget',
            '/UnoApiHeadersTarge/',
            '/UnpackedTarball',
            '/YaccTarget',
            '/unxlngx6.pro/CustomTarget',
            '/unxlngx6.pro/LexTarget',
            '/unxlngx6.pro/UnoApiHeadersTarget',
            '/unxlngx6.pro/UnpackedTarball',
            '/unxlngx6.pro/YaccTarget'],
    'Thunderbird':['/comm','/home/sylvestre/dev/mozilla/comm-central',
                   '/mozilla/directory/c-sdk','/mozilla','/obj-coverity','/obj-x86_64-pc-linux-gnu',
                   '/var/lib/jenkins/workspace/thunderbird-coverity'],
    'VTK':['/home/ken/Documents/vtk/vtk','/home/nschloe/software/vtk/source-upstream']
    }

def startswithAny(s, checks):
    for check in checks:
        if s.startswith(check):
            return check
    return False

def get_duplicates(projectId,files):
    q='select name from project where id=%s'
    project=sql.execute(q,(projectId,))[0]['name']
    if project not in hm:
        return {}
    
    checks=hm[project]
    duplicates={}
    
    for item in files:
        filename=item['filepath_on_coverity']
        cut = startswithAny(filename, checks)
        if cut:
            corrected=filename[len(cut):]                                                          
            fileId=item['id']
            mainId=common.get_file_id(corrected,projectId)
            if mainId not in duplicates:
                duplicates[mainId]=[fileId]
            else:
                duplicates[mainId].append(fileId)
                
    return duplicates


def remove_duplicates(duplicates):
    logging.info("%s files have duplicates",len(duplicates.keys()))
    
    corrected=0
    for main_id in duplicates.keys():
        ids=duplicates[main_id]

        for replace_id in ids:
            #update alerts
            q='update alert set file_id=%s where file_id=%s'
            sql.execute(q,(main_id, replace_id))

            # #update occurrences
            # query="update occurrence set file_id="+str(main_id)+" where file_id="+str(replace_id)
            # execute(query)

            #delete from files
            q='delete from file where id=%s'
            sql.execute(q,(replace_id,))

            corrected+=1
            
    return corrected
def resolve_filename_prefixes(projectId):
    files=get_all_files(projectId)

    duplicates= get_duplicates(projectId,files)
    
    if not duplicates:
        logging.info("no duplicates")
        return
    
    corrected = remove_duplicates( duplicates)

    logging.info("%s files have been corrected", corrected)
 
   
   
if __name__=='__main__':
    #read the project name
    project=sys.argv[1]
    projectId=common.get_project_id(project)
    
    print(get_base_names(get_all_files(projectId)))

