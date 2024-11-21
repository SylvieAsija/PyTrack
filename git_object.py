import collections
import hashlib
from math import ceil
import os
import re
import zlib
from git_repository import repo_file, repo_dir

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
    sha = object_resolve(repo, name)
    
    if not sha:
        raise Exception(f'No such reference {name}')

    if len(sha) > 1:
        raise Exception(f'Ambiguous reference {name}: Candidates are:\n - {sha}')
    
    sha = sha[0]
    
    if not fmt:
        return sha
    
    while True:
        obj = object_read(repo, sha)
        
        if obj.fmt == fmt:
            return sha
        
        if not follow:
            return None
        
        if obj.fmt == b'tag':
            sha = obj.kvlm[b'object'].decode('ascii')
        elif obj.fmt == b'commit' and fmt == b'tree':
            sha = obj.kvlm[b'tree'].decode('ascii')
        else:
            return None
    
class GitBlob(GitObject):
    fmt = b'blob'
    
    def serialize(self):
        return self.blobdata
    
    def deserialize(self, data):
        self.blobdata = data
        
class GitCommit(GitObject):
    fmt = b'commit'
    
    def serialize(self, data):
        return kvlm_serialize(self.kvlm)
    
    def deserialize(self, data):
        self.kvlm = kvlm_parse(data)
        
    def init(self):
        self.kvlm = dict()

def kvlm_parse(raw, start=0, dct=None):
    if not dct:
        dct = collections.OrderedDict()
    
    space = raw.find(b' ', start)
    newline = raw.find(b'\n', start)

    if space < 0 or newline < space:
        assert newline == start
        dct[None] = raw[start + 1:]
        return dct
    
    key = raw[start:space]
    end = start
    while True:
        end = raw.find(b'\n', end + 1)
        if raw[end + 1] != ord(' '):
            break
    
    value = raw[space + 1:end].replace(b'\n ', b'\n')
    
    if key in dct:
        if type(dct[key] == list):
            dct[key].append(value)
        else:
            dct[key] = [dct[key], value]
    
    return kvlm_parse(raw, start=end + 1, dct=dct)

def kvlm_serialize(kvlm):
    ret = b''
    
    for k in kvlm.keys():
        if k == None:
            continue
        
        val = kvlm[k]
        if type(val) != list:
            val = [val]
        
        for v in val:
            ret += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'

    ret += b'\n' + kvlm[None] + b'\n'
    
    return ret

class GitTreeLeaf(object):
    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha
        
def tree_parse_one(raw, start=0):
    x = raw.find(b' ', start)
    assert x-start == 5 or x-start == 6
    
    mode = raw[start:x]
    if len(mode) == 5:
        mode = b' ' + mode
    
    y = raw.find(b'\x00', x)
    path = raw[x+1:y]
    
    raw_sha = int.from_bytes(raw[y+1:y+21], 'big')
    sha = format(raw_sha, '040x')
    
    return y + 21, GitTreeLeaf(mode, path.decode('utf8'), sha)

def tree_parse(raw):
    pos = 0
    max = len(raw)
    ret = list()
    while pos < max:
        pos, data = tree_parse_one(raw, pos)
        ret.append(data)
    
    return ret

def tree_leaf_sort_key(leaf):
    if leaf.mode.startswith(b'10'):
        return leaf.path
    else:
        return leaf.path + '/'

def tree_serialize(obj):
    obj.items.sort(key=tree_leaf_sort_key)
    ret = b''
    for i in obj.items:
        ret += i.mode
        ret += b' '
        ret += i.path.encode('utf8')
        ret += b'\x00'
        sha = int(i.sha, 16)
        ret += sha.to_bytes(20, byteorder='big')
    return ret    
    
class GitTree(GitObject):
    fmt = b'tree'
    
    def deserialize(self, data):
        self.items = tree_parse(data)
    
    def serialize(self):
        return tree_serialize(self)
    
    def init(self):
        self.items = list()


class GitTag(GitObject):
    fmt = b'tag'

def ref_resolve(repo, ref):
    path = repo_file(repo, ref)
    
    if not os.path.isfile(path):
        return None
    
    with open(path, 'r') as fp:
        data = fp.read()[:-1]
    
    if data.startswith('ref: '):
        return ref_resolve(repo, data[5:])
    else:
        return data
    
def ref_list(repo, path=None):
    if not path:
        path = repo_dir(repo, 'refs')
    
    ret = collections.OrderedDict()
    
    for f in sorted(os.listdir(path)):
        can = os.path.join(path, f)
        if os.path.isdir(can):
            ret[f] = ref_list(repo, can)
        else:
            ret[f] = ref_resolve(repo, can)
    
    return ret

def object_resolve(repo, name):
    candidates = list()
    hashRE = re.compile(r'^[0-9A-Fa-f]{4,40}$')
    
    if not name.strip():
        return None
    
    if name == 'HEAD':
        return [ref_resolve(repo, 'HEAD')]
    
    if hashRE.match(name):
        name = name.lower()
        prefix = name[0:2]
        path = repo_dir(repo, 'objects', prefix, mkdir=False)
        if path:
            rem = name[2:]
            for f in os.listdir(path):
                if f.startswith(rem):
                    candidates.append(prefix + f)
    
    as_tag = ref_resolve(repo, 'refs/tags/' + name)
    if as_tag:
        candidates.append(as_tag)
    
    as_branch = ref_resolve(repo, 'refs/heads/' + name)
    if as_branch:
        candidates.append(as_branch)
        
    return candidates

class GitIndexEntry(object):
    def __init__(self, ctime=None, mtime=None, dev=None, ino=None, mode_type=None, 
                 mode_perms=None, uid=None, gid=None, fsize=None, sha=None, 
                 flag_assume_valid=None, flag_stage=None, name=None):
        
        self.ctime = ctime
        self.mtime = mtime
        self.dev = dev
        self.ino = ino
        self.mode_type = mode_type
        self.mode_perms = mode_perms
        self.uid = uid
        self.gid = gid
        self.fsize = fsize
        self.sha = sha
        self.flag_assume_valid = flag_assume_valid
        self.flag_stage = flag_stage
        self.name = name

class GitIndex(object):
    version = None
    entres = []
    
    def __init__(self, version=2, entries=None):
        if not entries:
            entries = list()
        
        self.version = version
        self.entries = entries

def index_read(repo):
    index_file = repo_file(repo, 'index')
    
    if not os.path.exists(index_file):
        return GitIndex()
    
    with open(index_file, 'rb') as f:
        raw = f.read()
    
    header = raw[:12]
    signature = header[:4]
    assert signature == b'DIRC'
    version = int.from_bytes(header[4:8], 'big')
    assert version == 2, 'wyag only supports index file version 2'
    count = int.from_bytes(header[8:12], 'big')
    
    entries = list()
    
    content = raw[12:]
    idx = 0
    for i in range(0, count):
        ctime_s = int.from_bytes(content[idx:idx+4], 'big')
        ctime_ns = int.from_bytes(content[idx+4:idx+8], 'big')
        mtime_s = int.from_bytes(content[idx+8:idx+12], 'big')
        mtime_ns = int.from_bytes(content[idx+12:idx+16], 'big')
        dev = int.from_bytes(content[idx+16:idx+20], 'big')
        ino = int.from_bytes(content[idx+20:idx+24], 'big')
        unused = int.from_bytes(content[idx+24:idx+26], 'big')
        assert 0 == unused
        mode = int.from_bytes(content[idx+26:idx+28], 'big')
        mode_type = mode >> 12
        assert mode_type in [0b1000, 0b1010, 0b1110]
        mode_perms = mode & 0b0000000111111111
        uid = int.from_bytes(content[idx+28:idx+32], 'big')
        gid = int.from_bytes(content[idx+32:idx+36], 'big')
        fsize = int.from_bytes(content[idx+36:idx+40], 'big')
        sha = format(int.from_bytes(content[idx+40:idx+60], 'big'), '040x')
        flags = int.from_bytes(content[idx+60:idx+62], 'big')
        flag_assume_valid = (flags & 0b1000000000000000) != 0
        flag_extended = (flags & 0b0100000000000000) != 0
        assert not flag_extended
        flag_stage =  flags & 0b0011000000000000
        name_length = flags & 0b0000111111111111
        
        idx += 62
        
        if name_length < 0xFFF:
            assert content[idx + name_length] == 0x00
            raw_name = content[idx:idx + name_length]
            idx += name_length + 1
        else:
            print('Notice: Name is 0x{:X} bytes long'.format(name_length))
            null_idx = content.find(b'\x00', idx + 0xFFF)
            raw_name = content[idx:null_idx]
            idx = null_idx + 1
        
        name = raw_name.decode('utf8')
        
        idx = 8 * ceil(idx/8)
        
        entries.append(GitIndexEntry(ctime=(ctime_s, ctime_ns), 
                                     mtime=(mtime_s, mtime_ns), 
                                     dev=dev, 
                                     ino=ino, 
                                     mode_type=mode_type, 
                                     mode_perms=mode_perms, 
                                     uid=uid, 
                                     gid=gid, 
                                     fsize=fsize, 
                                     sha=sha, 
                                     flag_assume_valid=flag_assume_valid, 
                                     flag_stage=flag_stage, 
                                     name=name))
    
    return GitIndex(version=version, entries=entries)