import r6s
import os
import sys
import pathlib as pth
import r6s.collector
import r6s.common
import r6s.asset
import json
import binstream


DUMP_PATH = (pth.Path.cwd() / './assets').resolve()
idir = pth.Path(r6s.settings.IMPORT)
data = r6s.collector.SiegeLinksData()
# data = r6s.collector.SiegeLinksData(load=False); data.generate()

UID = 220652921502  # caveira head FaZe diffuse texture uid
#UID = 22439848753  # MP5

not_found_msg = """
No assets that contain child with {uid} found. Why this happens?
There are tons of resources in game that are mostly used in maps.
Those are never referenced in asset files. To find asset-related
resources, use filters in roam scripts. There are certain
parameters, that allow to at least partially limit search to
char and weapons related files.
"""

def process_texture(dump_dir, forge, uid, entry_index):
    idx = entry_index['index']
    tex = r6s.tex.Tex(forge.get_container(idx).file.getstream())
    try:
        result = tex.buildPng(dump_dir)
        return result
    except RuntimeError as e:
        print(e)
        return None

def process_mesh(dump_dir, forge, uid, entry_index):
    idx = entry_index['index']
    r = forge.get_container(idx).file.getstream()
    mesh = r6s.mesh.Mesh(r)
    result = mesh.build_meshdata()
    out_file = dump_dir / f'{uid}.meshjson'
    with open(out_file, 'w') as w:
        try:
            json.dump(result,w)
        except TypeError as e:
            print('failed at',w)
            raise e
    return out_file

def process_asset(dump_dir, forge, uid, entry_index):
    shaders_dir = dump_dir / 'shaders'
    if not shaders_dir.is_dir():
        shaders_dir.mkdir()
    SHADER_MAGIC = 0x1C9A0555
    
    idx = entry_index['index']
    r = forge.get_container(idx).file.getstream()
    assets = r6s.asset.split_asset(r)
    shaders = r6s.asset.filter_by_magic(assets, SHADER_MAGIC)
    
    for shader in shaders:
        _, _, data = shader
        uid, magic = binstream.ruint64(data), binstream.ruint32(data)
        vert, frag, tail = r6s.asset.parse_shader(data)
        with open(shaders_dir / f'{uid}_vert.txt', 'w') as w:
            print(w.name)
            w.write(vert)
        with open(shaders_dir / f'{uid}_frag.txt', 'w') as w:
            print(w.name)
            w.write(frag)
        with open(shaders_dir / f'{uid}_tail.bin', 'wb') as w:
            print(w.name)
            w.write(tail)
    
    
def STOP(): raise Exception("STOP")

asset_links = data.asset_children.child_in_links(UID)
if asset_links is None:
    print(not_found_msg.format(uid=UID))
for asset_link in asset_links:
    print('='*40)
    print(asset_link)
    # prepare dir for asset data
    asset_dir = DUMP_PATH / f'{asset_link.src}'
    asset_dir.mkdir(parents=True, exist_ok=True)
    # find all children of given asset
    children = data.asset_children.children_uids(asset_link.src)
    forges = set()
    
    ## process is a list of attributes for processor. each entry is a lost of
    ## [function to process given data, dump directory, link object from depgraph, ]
    # set asset file itself to be processed
    index = data.uids_index.get(asset_link.src, None)
    process = [[process_asset, asset_dir, asset_link.src, index]]
    forges.add(index['forge'])
    
    for child_uid in children:
        print(child_uid,end=' ')
        index = data.uids_index.get(child_uid, None)
        if index is None:
            print('(no entry found)')
            continue
        magic = index['magic']
        if r6s.tex.is_texture(magic):
            print('is a texture')
            process.append([process_texture, asset_dir, child_uid, index])
            forges.add(index['forge'])
        elif r6s.mesh.is_mesh(magic):
            print('is a mesh')
            process.append([process_mesh, asset_dir, child_uid, index])
            forges.add(index['forge'])
        else:
            print('unresolved, skipped')
    
    # process all files and dump filtered data
    #continue
    print('\n\n\n')
    for forge_path in forges:
        with r6s.forge.parse(idir / forge_path) as forge:
            print(f'exporting from {forge_path}')
            for processor, asset_dir, child_uid, index in (x for x in process if forge_path == x[3]['forge']):
                result = processor(asset_dir, forge, child_uid, index)
        # print(index['forge'], index['index'])
        
input('done, press enter to close')