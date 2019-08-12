
import re
import subprocess
import sys

class Settings:
    def __init__(self):
        self.SALESFORCE_API_VERSION = '45.0'

    def parse_access(self, stdout):
        self.org_id = re.search('Access org (.*?) ', stdout).groups()[0]
        self.env = re.search('as user (.*?) with', stdout).groups()[0]
        self.base_token = re.search('sid=(.*)', stdout).groups()[0]
        self.instance_url = re.search('following URL: (.*?)/secur',stdout).groups()[0]
        self.login_url = re.search('following URL: (.*?)\\\\',stdout).groups()[0]
        return self
    def get_sid(self, rs):
        for name, value in rs.cookies.items():
            if name == 'sid':
                self.access_token = value


def is_valid_email(email):
    if re.match("(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email) != None:
        return True
    return False

def get_remote_origin_head(repo):
    master = None
    for remote in repo.remotes:
        if remote.name != 'origin':
            continue
        for ref in remote.refs:
            try:
                if ref.ref.remote_head == 'master' and ref.remote_head == 'HEAD':
                    master = ref
                    break
            except Exception as e:
                print(e)
    return master

def get_env(cwd):
    environments = []
    rs = subprocess.run(['sfdx','force:org:list'], cwd = cwd, stdout=subprocess.PIPE)
    print('enter the number for the environment you want to deploy to:')
    for i, v in enumerate(str(rs.stdout).split('\\n')):
        if i > 2:
            for u in v.split(' '):
                if is_valid_email(u):
                    environments.append(u)
    return environments

def select_env(environments):
    for i, env in enumerate(environments):
        print(str(i+1) + ')\t' + env)

    try:
        rs = input('Enter Number (1 - ' + str(len(environments)) + ', Ctrl+C to cancel) : ')
        selection = int(rs)
        return environments[selection - 1]
    except:
        print('that is not a valid selection')
        sys.exit()

def is_feature_branch(branch_name):
    if not branch_name.lower().startswith('feature/') :
        return False
    for key in re.findall('((?<!([A-Za-z])-)[A-Z]+-\d+)', branch_name ):
        return True
    return False

def is_release_branch(branch_name):
    if not branch_name.lower().startswith('release/') :
        return False
    return True

def is_valid(path):
    if 'force-app/main/default' in path:
        return True
    return False

def preflight(path):
    if ' '  in path:
        return '"' + path + '"'
    return path