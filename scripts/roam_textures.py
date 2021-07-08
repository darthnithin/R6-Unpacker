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
forge_name = 'datapc64_merged_bnk_textures3.forge'
start=0
stop=1_000_000
step=1


forge_dir_name, _ = os.path.splitext(forge_name)
dump = os.path.join(os.getcwd(), 'textures', forge_dir_name)
os.makedirs(dump, exist_ok=True)
count_exported = 0  # counter built for filtering purposes
with r6s.forge.parse(os.path.join(FORGES, forge_name)) as forge:
    # limit search to avoid out-of-bounds error
    start = max(start, 0)
    stop = min(stop, len(forge.entries))
    # loop through forge entries (compressed files)
    for i,e,n,c in forge[range(start,stop,step)]:
        print(f'{i:8d}',end='\r')
        # check if it's a texture
        if r6s.tex.is_texture(n.file_type):
            # parse testure metadata
            with r6s.tex.Tex(c.file.getstream()) as tex:
                # get real dimensions
                w,h = tex.get_dimensions()
                
                
                # only accept diffuse textures that are >= 512x512
                # you can add extra filter conditions here
                if (
                    w < 512  # only images that are wider than 512px
                    or h <512  # only images that are taller than 512px
                    or tex.tex_type != 0  # see.r6s.tex.Tex.tex_type
                    
                    # tex.tex_type in (1, 2, 4, 5, 7)   # filters non diffuse or icon textures
                    
                    # most face textures are 1:2 so we can use it to filter out
                    # a lot of garbage. For guns you will have to remove this check
                    or (h!=w*2)
                ): continue
                
                
                
                print(f'{i:8d}: {e.uid}')
                # save texture that passed filters
                try:
                    # some rare textures fail to get exported so we this it with
                    # an error handling closure
                    tex.buildPng(dump)
                except RuntimeError as e:
                    print(e)
                
                count_exported+=1
input(f'total exported: {count_exported}')