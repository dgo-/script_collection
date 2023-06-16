#!/usr/bin/env python3

import sys
import os
import requests

SESSION = requests.session()

def update_project_settings(project_id):
    url = f'{base_url}/projects/{project_id}'
    r = SESSION.put(url, data={
        "squash_option": "default_on",
        "remove_source_branch_after_merge": True,
        "only_allow_merge_if_pipeline_succeeds": True,
    })
    if not r.ok:
        print(f'Failed to set project config for project {project_id} with {r.status_code}.')
        return False

    return True

def update_project_approval_settings(project_id):
    url = f'{base_url}/projects/{project_id}/approvals'
    r = SESSION.post(url, data={
        "reset_approvals_on_push": True,
        "merge_requests_author_approval": False,
    })

    if not r.ok:
        print(f'Failed to set project approval config for project {project_id} with {r.status_code}.')
        return False

    return True

def update_project_approval_rule(project_id, approval_group_ids):
    url = f'{base_url}/projects/{project_id}/approval_rules'
    r = SESSION.get(url)

    if not r.ok:
        print(f'Failed to get project approval rules for project {project_id} with {r.status_code}.')
        return False

    # Skip if there are already approval rules defined
    if len(r.json()) > 0:
        print(f'Skipped project {project_id}, because approval rule is already defined.')
        return True

    r = SESSION.post(url, data={
        "name": "SRE Approval",
        "approvals_required": 1,
        "applies_to_all_protected_branches": True,
        "group_ids": approval_group_ids
    })
    if not r.ok:
        print(f'Failed to create project approval rule for project {project_id} with {r.status_code}.')
        return False

    return True

def protect_branch(project_id, branch_name):
    url = f'{base_url}/projects/{project_id}/protected_branches'

    r = SESSION.delete(f'{url}/{branch_name}')
    if r.status_code != 404 and not r.ok:
        print(f'Failed to delete old branch protection {project_id} with {r.status_code}.')
        return False

    r = SESSION.post(url, data={
        "name": branch_name,
        "push_access_level": 0,  # no one
        "merge_access_level": 40 # maintainer
    })

    if not r.ok:
        print(f'Failed to create branch protection {project_id} with {r.status_code}.')
        return False

    return True

def configure_project(project_id, approval_group_ids, branch_name):
    if not update_project_settings(project_id):
        return False

    if not update_project_approval_settings(project_id):
        return False

    if not update_project_approval_rule(project_id, approval_group_ids):
        return False

    if not protect_branch(project_id, branch_name):
        return False

    return True

def configure_projects(group_id, approval_group_ids, branch_name):
    url = f'{base_url}//groups/{group_id}/projects?per_page=40&page=1'

    r = SESSION.get(url)
    if not r.ok:
        print(f'Failed load projects with {r.status_code}.')
        return False

    for project in r.json():
        if project["archived"]:
            print(f'Skipped archived project: {project["name"]} - {project["id"]}')
            continue
        print(f'Staring project: {project["name"]} - {project["id"]}')
        if configure_project(project["id"], approval_group_ids, branch_name):
            print(f'Successfully finisched project: {project["name"]} - {project["id"]}')
        else:
            print(f'Failed project: {project["name"]} - {project["id"]}')

    return True

if __name__ == "__main__":
    """
    The envrionment variables need to be set
    GITLAB_URL   = "https://gitlab.com"
    GITLAB_TOKEN = "secret"
    """
    base_url = os.environ.get('GITLAB_URL') + "/api/v4"
    token = os.environ.get('GITLAB_TOKEN')
    if not base_url and not token:
        print("Please set GITLAB_URL and GITLAB_TOKEN")
        sys.exit(1)

    SESSION.headers.update({"Authorization": "Bearer %s" % (token)})


    # config
    """ project_ids: List of project_ids: Contains project_ids of projects that should be updates. """
    project_ids = []
    """ group_ids: List of group_ids. It will update all projects in the group"""
    group_ids = []
    """approval_group_ids: List of group_ids. This groups ids will set a approver on MR"""
    approval_group_ids = []
    """branch_name: The name of the branch, which will be protected """
    branch_name = "main"


    # configure single project
    for project_id in project_ids:
        print(f'Staring project {project_id}')
        if configure_project(project_id, approval_group_ids, branch_name):
            print(f'Successfully finisched project {project_id}')
        else:
            print(f'Failed project {project_id}')

    # configure group
    for group_id in group_ids:
        print(f'Staring group {group_id}')
        if configure_projects(group_id, approval_group_ids, branch_name):
            print(f'Successfully finisched group {group_id}')
        else:
            print(f'Failed project: {group_id}')
