import csv
from getpass import getpass
import requests
import json
from keycloak import KeycloakOpenID
import settings


#Fuction to get access token from Keycloak for auth at ocis
def getToken():
    space_admin_password = getpass('Password for ' + settings.space_admin_user +':')

    keycloak_openid = KeycloakOpenID(server_url=settings.keycloak_url,
                                    client_id=settings.keycloak_client_id,
                                    realm_name=settings.keycloak_realm,
                                    client_secret_key=settings.keycloak_client_secret)

    token = keycloak_openid.token(settings.space_admin_user, space_admin_password)
    return token['access_token']

#Fuction to check for existing spaces with the same name
def findDriveName(data, search_string):
    for thing in data['value']:
        if thing['name'] == search_string:
            return thing['id']
    return None

def spaceProvisioning():
    #Open csv
    with open(settings.csv_file, newline='') as csvfile:
        spamreader = csv.DictReader(csvfile, delimiter=';', quotechar='|')
        
        #Create Header with access token
        headersAPI = {
            'accept': 'application/json',
            'Authorization': 'Bearer '+ getToken(),
        }

        #Get permission IDs 
        url = "{0}graph/v1beta1/roleManagement/permissions/roleDefinitions".format(settings.ocis_url)
        r = requests.get(url, headers=headersAPI)

        #Set Permission ids
        for role in r.json():
            if role['displayName'] == "Space Viewer":
                settings.space_viewer_id = role["id"]
            elif role['displayName'] == "Space Editor":
                settings.space_editor_id = role["id"]
            elif role['displayName'] == "Manager":
                settings.space_manager_id = role["id"]

        #Check each 
        for row in spamreader:
            #Get Id if Space is already there
            url = "{0}graph/v1.0/drives".format(settings.ocis_url)
            r = requests.get(url, headers=headersAPI)
            if settings.script_debug:
                print(row)
            if r.status_code == 200:
                data = r.json()
                drive_name = findDriveName(data, row[settings.space_name_field])
                if drive_name:
                    if settings.script_debug:
                        print('Found drive with ID: ' + drive_name)
                    space_id = drive_name
                else:
                    insert = {"name": row[settings.space_name_field],"quota": {"total": 1000000000},"description": row[settings.space_description_field]}
                    url = "{0}graph/v1.0/drives".format(settings.ocis_url)
                    r = requests.post(url, headers=headersAPI, json=insert)
                    if settings.script_debug:
                        print("Space created with id: " + r.json()['id'])
                    space_id = r.json()['id']
                #url = "{0}graph/v1.0/users?%24search={1}".format(settings.ocis_url, row[settings.user_name_field])
                #r = requests.get(url, headers=headersAPI)

                if row[settings.user_role_field] == settings.manager_string:
                    role_id = "manager"
                elif row[settings.user_role_field] == settings.editor_string:
                    role_id = "editor"
                else:
                    role_id = "viewer"
                if settings.script_debug:
                    print(r.json()['value'][0]['id'] + ' needs ' + role_id )
                
                space_id = space_id.replace("$","%24")
                url = "{0}ocs/v1.php/apps/files_sharing/api/v1/shares?shareType=7&shareWith={1}&space_ref={2}&permissions=1&role={3}".format(settings.ocis_url, row[settings.user_name_field], space_id, role_id)
                r = requests.post(url, headers=headersAPI)
            else:
                if settings.script_debug:
                    print(r.status_code)

if __name__ == "__main__":
    spaceProvisioning()

