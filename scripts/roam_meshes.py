"""
This is an example script that allows one to dump a set of textures.
It's set up in such a way that it filters out first 100 textures from
biggest texture forge. It's also set up to catch mostly vertical images
so that it's easier to find faces. You can edit filters to suit your
needs. To access specific parameters read r6s source code. I tried to
keep it as tidy as possible for a research code.
"""
import r6s
import os
import pathlib as pth



FORGES = r6s.settings.IMPORT  # can be replaced with custom path to forges
# export range limiter so you don't accidentally unpack a couple gigs of textures
forge_name = 'datapc64_merged_bnk_mesh.forge'
start=0
stop=1_000_000
step=1


forge_dir_name, _ = os.path.splitext(forge_name)
dump = os.path.join(os.getcwd(), 'meshes', forge_dir_name)
os.makedirs(dump, exist_ok=True)
count_exported = 0  # counter built for filtering purposes
with r6s.forge.parse(os.path.join(FORGES, forge_name)) as forge:
    #print(f'total amount of entries in file: {len(forge.entries)}')
    # limit search to avoid out-of-bounds error
    start = max(start, 0)
    stop = min(stop, len(forge.entries))
    # loop through forge entries (compressed files)
    for i,e,n,c in forge[range(start,stop,step)]:
        print(f'{i:8d}',end='\r')
        # check if it's a mesh
        if r6s.mesh.is_mesh(n.file_type):
            # parse testure metadata
            try:
                with r6s.mesh.Mesh(c.file.getstream(), readmesh=False) as mesh:
                    
                    # filter meshes that most likely belong to guns
                    if (
                        #mesh.x2C not in (9,10)  # see r6s.mesh.Mesh.x2C
                        mesh.num_verts < 100
                    ): continue


                    mesh.readmesh()
                    print(f'{i:8d}: {e.uid}')
                    # save mesh that passed filters
                    mesh.dump_meshdata(dump)
                    
                    count_exported+=1
            except Exception as e:
                #print(f'{i:8d}: {e.uid} - FAILED\n{err}')
                pass
input(f'total exported: {count_exported}')