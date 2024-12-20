import configparser
import os


class GitRepository(object):
    
    worktree = None
    gitdir = None
    conf = None
    
    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, '.git')
        
        if not (force or os.path.isdir(self.gitdir)):
            raise Exception(f'Not a Valid Git Repository {path}')
        
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, 'config')
        
        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception('Configuration File Missing')
        
        if not force:
            vers = int(self.conf.get('core', 'repositoryformatversion'))
            if vers != 0:
                raise Exception(f'Unsupported Repository Format Version {vers}')

def repo_path(repo, *path):
    return os.path.join(repo.gitdir, *path)

def repo_file(repo, *path, mkdir=False):
    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)

def repo_dir(repo, *path, mkdir=False):
    path = repo_path(repo, *path)
    
    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        else:
            raise Exception(f'Not a Valid Directory {path}')
    
    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None
    
def repo_create(path):
    repo = GitRepository(path, True)
    
    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception(f'{path} is Not a Directory')
        if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
            raise Exception(f'{path} is Not Empty')
    else:
        os.makedirs(repo.worktree)

        
    assert repo_dir(repo, 'branches', mkdir=True)
    assert repo_dir(repo, 'objects', mkdir=True)
    assert repo_dir(repo, 'refs', 'tags', mkdir=True)
    assert repo_dir(repo, 'refs', 'heads', mkdir=True)
    
    with open(repo_file(repo, 'description'), 'w') as f:
        f.write('Unnamed repository; edit this file \'description\' to name the repository')
    
    with open(repo_file(repo, 'HEAD'), 'w') as f:
        f.write('ref: refs/heads/master\n')
        
    with open(repo_file(repo, 'config'), 'w') as f:
        config = repo_default_config()
        config.write(f)
    
    return repo

def repo_default_config():
    ret = configparser.ConfigParser()
    
    ret.add_section('core')
    ret.set('core', 'repositoryformatversion', '0')
    ret.set('core', 'filemode', 'false')
    ret.set('core', 'bare', 'false')
    
    return ret

def repo_find(path="", required=True):
    
    path = os.path.realpath(path)
    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepository(path)

    parent = os.path.realpath(os.path.join(path, ".."))
    
    if parent == path:
        if required:
            raise Exception("No git directory")
        else:
            return None
    
    return repo_find(parent, required)
