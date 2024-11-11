import configparser
import os


class GitRepository (object):
    
    worktree = None
    gitdir = None
    conf = None
    
    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")
        
        if not (force or os.path.isdir(self.gitdir)):
            raise Exception("Not a Valid Git Repository ", path)
        
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")
        
        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception("Configuration File Missing")
        
        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception("Unsupported Repository Format Version ", vers)

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
            raise Exception("Not a Valid Directory ", path)
    
    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None
        