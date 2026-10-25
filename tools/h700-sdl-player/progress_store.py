"""Copy and restore only the SharedObjects captured by the selected game."""
import json, os, tempfile
from pathlib import Path, PurePosixPath

def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def object_path(root, name):
    if not isinstance(name,str) or not name or '\\' in name or ':' in name:
        raise ValueError('Nome de save invalido')
    relative=PurePosixPath(name+'.sol')
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Caminho de save invalido')
    path=Path(root).joinpath(*relative.parts)
    if not path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Save fora da pasta do jogo')
    if any(p.is_symlink() for p in [path,*path.parents] if p != Path(root).parent):
        raise ValueError('Link simbolico no save')
    return path

def read_snapshot(root, game):
    name=Path(game).stem
    path=Path(root)/'progress'/(name+'.json')
    with path.open(encoding='utf-8') as f: snapshot=json.load(f)
    if snapshot.get('version') != 1 or snapshot.get('game') != name or not isinstance(snapshot.get('objects'),dict):
        raise ValueError('Copia nao pertence a este jogo ou formato invalido')
    entries=[]
    for key,value in snapshot['objects'].items():
        target=object_path(root,key)
        if value is not None and (not isinstance(value,list) or any(type(x) is not int or not 0<=x<=255 for x in value)):
            raise ValueError('Dados de save invalidos')
        entries.append((key,target,None if value is None else bytes(value)))
    if not entries or not any(data is not None for _,_,data in entries):
        raise ValueError('A copia nao contem progresso salvo')
    return entries

def restore(root,game):
    entries=read_snapshot(root,game)
    before={key:list(path.read_bytes()) if path.exists() else None for key,path,_ in entries}
    # Save the current files before replacing anything, including absent keys.
    backup={'version':1,'game':Path(game).stem,'objects':before}
    atomic_write(Path(root)/'progress'/(Path(game).stem+'.before-load.json'),json.dumps(backup).encode('utf-8'))
    changed=[]
    try:
        for key,path,value in entries:
            changed.append((key,path))
            if value is None:
                if path.exists(): path.unlink()
            else: atomic_write(path,value)
    except OSError:
        for key,path in reversed(changed):
            if before[key] is None:
                if path.exists(): path.unlink()
            else: atomic_write(path,bytes(before[key]))
        raise
