import hashlib
import os
import zlib
from git_repository import repo_file


class GitObject(object):
    
    def __init__(self, data=None):
        if data != None:
            self.deserialize(data)
        else:
            self.init()
        
    def serialize(self, repo):
        raise Exception('Unimplemented')
    
    def deserialize(self, data):
        raise Exception('Unimplemented')
    
    def init(self):
        pass

# maybe move to git repo file
def object_read(repo, sha):
    
    path = repo_file(repo, 'objects', sha[0:2], sha[2:])
    
    if not os.path.isfile(path):
        return None
    
    with open (path, 'rb') as f:
        raw = zlib.decompress(f.read())
        
        x = raw.find(b' ')
        fmt = raw[0:x]
        
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode('ascii'))
        if size != len(raw) - y - 1:
            raise Exception("Malformed Object {sha}: bad length")
        
        match fmt:
            case b'commit'  : c = GitCommit
            case b'tree'    : c = GitTree
            case b'tag'     : c = GitTag
            case b'blob'    : c = GitBlob
            case _          : raise Exception('Unknown Type \
                                              {fmt.decode(\'ascii\')} for object {sha}')
            
        return c(raw[y+1:])

def object_write(obj, repo=None):
    data = obj.serialize()
    
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data
    
    sha = hashlib.sha1(result).hexdigest()
    
    if repo:
        path = repo_file(repo, "objects", sha[0:2], sha[2:], mkdir=True)
        
        if not os.path.exists(path):
            with open (path, "wb") as f:
                f.write(zlib.compress(result))
    
    return sha

def object_find(repo, name, fmt=None, follow=True):
    return name