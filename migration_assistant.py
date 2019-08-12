import sys
import git
import os
import argparse

from packagebuilder import tasks
import requests

# pyinstaller migration_assistant.py --onefile

from lib import *


version = '1.01'

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

parser.add_argument('-c', '--checkonly',
                    help='validate only',
                    action='store_true',
                    required=False)

parser.add_argument('-p', '--path',
                    help='provide path to project repository, defaults to current directory',
                    required=False)

parser.add_argument('-s', '--snapshot',
                    help='get full package.xml and populate local folder',
                    action='store_true',
                    required=False)

args = parser.parse_args(sys.argv[1:])


try:

    if args.version:
        print('version ' + version )
        sys.exit()

    cwd = args.path if args.path else os.getcwd()
    if args.snapshot:
        if not args.username:
            print()
            print()

            print('searching for available environments')
            environments = get_env(cwd)
            if environments:
                environment = select_env(environments)
            else:
                print('no environments found, please connect to an org and try again')
                sys.exit()
        else:
            environment = args.username


        response = subprocess.run(['sfdx','force:org:open', '-u', environment], cwd = cwd, stdout=subprocess.PIPE)
        settings = Settings().parse_access(str(response.stdout))
        settings.get_sid(requests.get(settings.login_url))

        package = tasks.query_components_from_org(settings)
        if not os.path.isdir(os.path.join(cwd, 'manifest')):
            os.mkdir(os.path.join(cwd, 'manifest'))
        open(os.path.join(cwd, 'manifest') + '/package.xml','w').write(package.xml)

        print('retrieving metadata from', environment + ': be patient, this will take a bit of time.')
        command = ['sfdx','force:source:retrieve', '-u', environment,'-x','manifest/package.xml','--verbose']
        print('executing $',' '.join(command))

        response = subprocess.run(command, cwd = cwd)
        print(str(response.stdout))
        print('metadata retrieval complete')





    else:
        repo = git.Repo(cwd)
        master = get_remote_origin_head(repo)




        if is_feature_branch(repo.head.ref.name):
            try:
                repo.git.push('origin')
            except:
                pass
        elif is_release_branch(repo.head.ref.name):
            try:
                repo.git.push('origin')
            except:
                pass
        else:
            print('feature branches start with "feature/" and contain a JIRA key, example: feature/COES-1. ' + repo.head.ref.name + ' does not look like a feature branch')
            sys.exit()


        common_commit = repo.merge_base(repo.head, master)
        # print(repo.head, master, common_commit[0])
        rs = common_commit[0].diff(repo.head)
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

        print('capturing changes between master and current branch: ' + repo.head.ref.name)
        print(str(master) + '..' + str(repo.head))


        if not mod_adds and not deletions:
            print('no changes found to deploy, exiting')
            sys.exit()
        elif mod_adds or deletions:
            if not args.username:
                print()
                print()

                print('searching for available environments')
                environments = get_env(cwd)
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



except Exception as e:
    print(e)
    sys.exit()
