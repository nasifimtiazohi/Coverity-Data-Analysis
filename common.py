import sql

def is_number(n):
    try:
        int(n)
    except ValueError:
        return False
    return True

def read_xml_file_to_list_of_dicts(file):
    import xml.etree.ElementTree as ET
    tree = ET.parse(file)
    root = tree.getroot()

    datalist=[]
    for child in root:
        data=child.attrib
        datalist.append(data)
    
    return datalist

def get_project_id(project):
    q='select id from project where name=%s'
    results=sql.execute(q,(project,))
    if not results:
        raise Exception('project not yet added.')    
    return results[0]['id']



 