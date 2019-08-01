import sys
import git
import os
import pathlib
import argparse
import re
from distutils.util import strtobool

import uuid
import subprocess
import re
import numbers
import pyperclip

version = '1.0'

parser = argparse.ArgumentParser(description='creates a deployment package from the current feature branch')

parser.add_argument('-u', '--username',
                    help='provide the username',
                    required=False)

parser.add_argument('-v', '--version',
                    help='print version and exit',
                    action='store_true',
                    required=False)

parser.add_argument('-l', '--local-tests',
                    help='run local tests during deploy',
                    action='store_true',
                    required=False)

parser.add_argument('-checkonly', '--checkonly',
                    help='validate only',
                    action='store_true',
                    required=False)



parser.add_argument('-p', '--path',
                    help='provide path to project repository, defaults to current directory',
                    required=False)


args = parser.parse_args(sys.argv[1:])

def is_valid_email(email):
    if re.match("(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email) != None:
        return True
    return False

def get_remote_origin_head(repo):
    master_head = None
    for remote in repo.remotes:
        if remote.name != 'origin':
            continue
        for ref in remote.refs:
            try:
                if ref.ref.remote_head == 'master' and ref.remote_head == 'HEAD':
                    master_head = ref.commit
                    break
            except Exception as e:
                print(e)
    return master_head

def get_env():
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

def is_valid(path):
    if 'force-app/main/default' in path:
        return True
    return False

def preflight(path):
    if ' '  in path:
        return '"' + path + '"'
    return path


try:

    if args.version:
        print('version ' + version )
        sys.exit()




    cwd = args.path if args.path else os.getcwd()

    repo = git.Repo(cwd)
    master_head = get_remote_origin_head(repo)

    head = repo.head.commit


    if not is_feature_branch(repo.head.ref.name):
        print('feature branches start with "feature/" and contain a JIRA key, example: feature/COES-1. ' + repo.head.ref.name + ' does not look like a feature branch')
        answer = input('Continue? (y/n)')
        if answer != 'Y' or answer != 'y':
            sys.exit()
    else:
        try:
            repo.git.push('origin')
        except:
            pass

    rs = master_head.diff(head)
    deletions = []
    mod_adds = []

    for change in rs:
        if change.change_type == 'M' or change.change_type == 'A':
            if is_valid(change.b_path):
                mod_adds.append(preflight(change.b_path))
        elif change.change_type == 'D':
            if is_valid(change.a_path):
                deletions.append(preflight(change.a_path))
        elif change.change_type == 'R':
            if is_valid(change.a_path):
                deletions.append(preflight(change.a_path))
            if is_valid(change.b_path):
                mod_adds.append(preflight(change.b_path))

    print('capturing changes between master and current feature: ' + repo.head.ref.name)
    print(str(master_head) + '..' + str(head))


    if not mod_adds and not deletions:
        print('no changes found to deploy, exiting')
        sys.exit()
    elif mod_adds or deletions:
        if not args.username:
            print()
            print()

            print('searching for available environments')
            environments = get_env()
            if environments:
                environment = select_env(environments)
            else:
                print('no environments found, please connect to an org and try again')
                sys.exit()
        else:
            environment = args.username

        print('found the following additive changes to deploy:')
        for f in mod_adds:
            print('\t' + f)

        print('would you like to deploy these changes to ' + environment + '?')

        command = ['sfdx','force:source:deploy','-u', environment, '-p', ','.join(mod_adds)]

        if args.local_tests:
            command.extend(['-l','RunLocalTests'])

        if args.checkonly:
            command.extend(['--checkonly'])

        answer = input('Deploy?(y/n): ')
        if answer == 'y'  or answer == 'Y':
            subprocess.run(command, cwd = cwd)
        else:
            print('here is the deployment line:\n' + ' '.join(command))
            pyperclip.copy(' '.join(command))


except KeyboardInterrupt:
    print()
    sys.exit()
