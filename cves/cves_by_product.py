import sys
sys.path.append('../main')
import common, sql
import requests 
import json, csv
import datetime, time

def make_cpe_string(type,vendor,product=None,version=None):
    if not vendor:
        return None

    cpe='cpe:2.3:'+type
    if not product:
        cpe= cpe+':*:'+vendor
    else:
        cpe= cpe+':'+vendor+':'+product
    
    if version:
        cpe += ':' + version
        
    return cpe

def get_product_cves(type, vendor,
                    product=None,
                    version= None, 
                    startDate=None, 
                    endDate=None):
    '''
    Retrieves cve for a product within a date range
    '''
    assert isinstance(startDate, datetime.datetime)
    assert isinstance(endDate, datetime.datetime)
    print(vendor,product,startDate,endDate) 
    startDate = startDate.strftime('%Y-%m-%d') + 'T00:00:00:000 UTC-05:00'
    endDate = endDate.strftime('%Y-%m-%d') + 'T00:00:00:000 UTC-05:00'
    resultsPerPage=100
    cpe=make_cpe_string(type,vendor,product,version)
    
    payload={
        'cpeMatchString':cpe,
        'pubStartDate':startDate,
        'pubEndDate':endDate,
        'startIndex':0,
        'resultsPerPage':resultsPerPage
    }

    fulllist={}
    
    idx=0
    totalResults=None #will be set in the loop
    while True:
        payload['startIndex']=idx
        data=requests.get('https://services.nvd.nist.gov/rest/json/cves/1.0/?',
                      params=payload)
        while data.status_code != 200:
            data=requests.get('https://services.nvd.nist.gov/rest/json/cves/1.0/?',
                      params=payload)
            print("site not responding")
        data=json.loads(data.content)
        if idx==0:
            totalResults=data['totalResults']
            print(totalResults)
        cves=data['result']['CVE_Items']
        print("running well", len(cves),idx)
        if not cves:
            break
        for cve in cves:
            id=cve['cve']['CVE_data_meta']['ID']
            if id in fulllist:
                raise Exception("duplicate CVE",id)
            fulllist[id]=cve
        idx+=resultsPerPage
    
    assert len(fulllist)==totalResults
    
    return fulllist

def get_project_cves(projectId):
    q='''select * from project p
        join product_info pi on p.id = pi.project_id
        where p.id=%s '''
    r=sql.execute(q,(projectId,))[0]
    type, vendor, product, startDate, endDate= r['type'], r['vendor'],r['product'],r['start_date'],r['end_date']
    fulllist = get_product_cves(type, vendor, product=product, startDate=startDate, endDate=endDate)
    cves=list(fulllist.keys())
    cves.sort(reverse=True)
    return cves

def get_description(cve):
    url='https://services.nvd.nist.gov/rest/json/cve/1.0/'+cve
    #print("started")
    r=requests.get(url)
    while r.status_code != 200:
        print(r.content)
        time.sleep(1)
        r=requests.get(url)
    data=json.loads(r.content)
    #print("ended")
    data=data['result']['CVE_Items'][0]
    description=data['cve']['description']['description_data'][0]['value']
    description=description.replace('"','')
    return description


def make_csv(projectName, cves):
    filename = projectName + 'cvelist.csv'
    print(filename)
    with open(filename, 'w') as file:
        writer=csv.writer(file)
        for i,cve in enumerate(cves):
            writer.writerow([cve, get_description(cve)])
            print(i)
     

if __name__=='__main__':
    project=sys.argv[1]
    q='select id, name from project where name=%s'
    results=sql.execute(q,(project,))
    for item in results:
        print(item['name'])
        projectId=item['id']
        cves=get_project_cves(projectId)
        print(len(cves))
        name=item['name']
        make_csv(name,cves)