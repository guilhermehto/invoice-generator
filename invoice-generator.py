import requests
import sys
import inquirer
import base64
import getpass

LOGIN_URL = 'https://www.toggl.com/api/v8/me'
REPORTS_URL = 'https://toggl.com/reports/api/v2/summary?workspace_id=%s&since=%s&user_agent=%s'

workspace = ""

login = input("Email: ")
password = getpass.getpass()
base64_secret = base64.b64encode(
    (str(login) + ':' + str(password)).encode('utf-8'))
auth_param = 'Basic ' + base64_secret.decode('utf-8')

request_json = requests.get(
    LOGIN_URL, headers={'Authorization': auth_param}).json()

workspace_names = []
for workspace in request_json['data']['workspaces']:
    workspace_names.append(workspace['name'])

options = [
    inquirer.List('workspace_name',
                  message='Choose workspace',
                  choices=workspace_names
                  ),
]

selected_workspace_name = inquirer.prompt(options)['workspace_name']
selected_workspace_id = ''

for workspace in request_json['data']['workspaces']:
    if workspace['name'] == selected_workspace_name:
        selected_workspace_id = workspace['id']
        break
api_token = request_json['data']['api_token']
base64_api_token = base64.b64encode((api_token + ':api_token').encode('utf-8'))
auth_param = 'Bearer ' + base64_api_token.decode('utf-8')

summary_url = REPORTS_URL % (selected_workspace_id, sys.argv[1], login)
entries = requests.get(summary_url, headers={
                       'Authorization': auth_param}).json()['data']

total_time = 0
projects = {}
project_names = []

for entry in entries:
    total_time += entry['time']
    items = []
    for item in entry['items']:
        items.append({
            'title': item['title']['time_entry'],
            'time': item['time']
        })
    projects[entry['title']['project']] = {
        'total_time': entry['time'],
        'items': items
    }

selected_projects = inquirer.prompt([
    inquirer.Checkbox('selected_projects',
                      message="Select projects", choices=projects.keys()),
])

invoice_file = open("%s-invoice.html" % sys.argv[1], "w")

generated_html = ""

title_template = """
                            <tr>
                                <th scope="row">%s</th>
                                <td></td>
                                <td></td>
                            </tr>
"""

item_template = """
                            <tr>
                                <th scope="row"></th>
                                <td>%s</td>
                                <td>%s</td>
                            </tr>
"""

total_selected_time = 0
for selected_project in selected_projects['selected_projects']:
    project_html = ""
    project_html += title_template % (selected_project)
    for item in projects[selected_project]['items']:
        floating_time = item['time'] / 1000.0 / 60.0 / 60.0
        total_selected_time += floating_time
        hours = int(floating_time) or 1
        minutes = int(floating_time % hours * 60.0)
        project_html += item_template % (item['title'],
                                         "%s h %s m" % (hours, minutes))
    generated_html += project_html


total_hours = int(total_selected_time)
total_minutes = int(total_selected_time % total_hours * 60.0)

generated_html += """
                    <div class="text-right">
                        <h4><b>Time Total: </b>%s h %s m</h4>
                        <h4><b>US$ Total: </b>%s,00</h4>
                    </div>
""" % (total_hours, total_minutes, total_selected_time * 16)

invoice_file.write(generated_html)
invoice_file.close()
