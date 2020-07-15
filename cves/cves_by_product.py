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
                    endDate=None,
                    getTotalCount=False):
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
            if getTotalCount:
                return totalResults
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

def get_project_cves(projectId, getTotalCount=False):
    q='''select * from project p
        join product_info pi on p.id = pi.project_id
        where p.id=%s '''
    r=sql.execute(q,(projectId,))[0]
    type, vendor, product, startDate, endDate= r['type'], r['vendor'],r['product'],r['start_date'],r['end_date']
    if getTotalCount:
        totalCount= get_product_cves(type, vendor, product=product, startDate=startDate, endDate=endDate,
                                     getTotalCount=True)
        return totalCount
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

def addFromNvdApi(cve):
    url='https://services.nvd.nist.gov/rest/json/cve/1.0/'+cve
    response=requests.get(url)
    while response.status_code != 200 :
        time.sleep(3)
        response=requests.get(url)
    print('feteched cve: ',cve)
    
    data=json.loads(response.content)
    data=data['result']['CVE_Items'][0]
    
    temp=data['cve']['problemtype']['problemtype_data'][0]['description']
    cwes=[]
    for t in temp:
        if 'CWE' in t['value']:
            if not 'NVD' in t['value']:
                cwes.append(int(t['value'].split('-')[1].strip()))    
            else:
                cwes.append(t['value'])
    
    description=data['cve']['description']['description_data'][0]['value']
    description=description.replace('"','')
    
    data=data['impact']
    severity2, score2, severity3, score3 = [None] * 4
    if 'baseMetricV2' in data.keys():
        t=data['baseMetricV2']
        severity2=t['severity']
        score2=t['cvssV2']['baseScore']
    if 'baseMetricV3' in data.keys():
        t=data['baseMetricV3']
        severity3= t['cvssV3']['baseSeverity']
        score3=t['cvssV3']['baseScore']
    
    for cwe in cwes:   
        insertQ='insert into cve values(%s,%s,%s,%s,%s,%s,%s)'
        try:
            sql.execute(insertQ,(cve, cwe, description, score2, severity2, score3, severity3))
        except sql.pymysql.IntegrityError as error:
            if error.args[0] == sql.PYMYSQL_DUPLICATE_ERROR:
                print(cve,cwe, ' already exists')

def insert_cves(projectId, cves):
    for cve in cves:
        addFromNvdApi(cve)
    

if __name__=='__main__':
    q='select * from product_info'
    results=sql.execute(q)
    for item in results:
        projectId=item['project_id']
        cves=get_project_cves(projectId)
        insert_cves(projectId, cves)