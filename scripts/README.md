About
=====
This is a collection of scripts designed to dump meshes and textures
with relatve ease.



Usage
=====
## 0. Before you begin
I do recommend you to run your scripts in an open cmd window. This stuff
works 99% of the time but when it fails, you want to be able to see the
error message so you can ask for help with it.

## 1. Optional (if your siege distro has updated)
Delete cache folder (by default it's called `cache`). This will force
scripts to rebuild cache data with updated game files.

## 2. Find some assets
There are 2 scripts intended for that porpose: `roam_textures.py` and
`roam_meshes.py`.

### Using roam_textures.py
Open it in your text editor and edit the values you need. Main ones are:
* `forge_name` - the file you want to roam
* `start`, `stop`, `step` - range of entries you want to scan. Some
  forges contain tens of thousands of entries, so trust me, you'd want
  to work in batches. Keep in mind, these are the ones that get scanned,
  not the ones that get exported. Only the ones that pass a filter are
  exported.
* you can modify code after `# you can add extra filter conditions here`
  to customize your filtering. To get more info on texture file
  attributes, read `r6s.tex.py` source code.

After runnig the script, it will create a `textures` folder where it
will dump all entries that had passed the filter. Each image will have
it's UID as a file name. Inspect the images and find one that is a part
of asset that interests you.

I'd suggest roaming `texture3.forge` forges, those are the biggest
resolution and are easier to inspect.

### Using roam_models.py
Same thing as with roam_textures. It reads a given file, it dumps out
meshes that please the filter into a `meshes` folder. One note that you
should know is you only need `mesh.forge` files, those are the ones that
contain meshes, not `meshshape.forge` ones (those contain havok collider
meshes and I don't parse those).

## 3. You have found a texture/mesh that interests you
Now, copy it's filename (it's UID). Open `dump_asset.py` and paste UID
into a `UID` variable. Run script.

What it will do is it will search for any assets that have this item as
a dependency. It will create a folder `assets/*asset_uid*`, and dump all
it's texture and mesh dependencies there. Keep in mind, your item might
be used in a bunch of assets, this script will dump each of those. In
the console window each asset is printed as
```
<Link: src=9890089146, dst=22439848753, x10=-1, x14=239, x16=8, x17=0>
```
with scr meing the asset uid (the name of newly created folder). If you
see 20 such lines in colsole, that means it had dumped 20 assets so
don't be surprised when you open your assets folder.

### IMPORTANT
UIDs in siege are persistent across time, i.e. don't change with
updates. Caveira's basic will always have same UID no matter what update
it is. So please, when you find a suitable asset, write down it's uids
(folder's uid as `asset`, meshes as `mesh`, textures as `tex`) and mark
them with some suitable comment, i.e.
```
220652921502: Caveira head, Faze Clan skin, diff texture
210322528513: Caveira head, Faze Clan skin, asset
```
and post them at xentax.com siege thread (better do it in batches).
I hope I will gather them inside `r6s` package and use for later
analysis of data.

## 4. getting asset into blender
Along with the scripts there is a `load_meshjson.blend` file. Open it
with blender (I used 2.91 at the time of making this README). You will
see a script window and a viewport with Cav's head and a basic mp5. To
load in your data, edit `fdir` in that script to point to your asset
dump and run the script (`play` button at the top of the script panel).
It will import all of the meshes that are present in that folder.
You will have to setup your materials by hand because I have not yet
reversed the asset structure. Example assets already contain some
example materials that aren't precise but should give you an idea of
how to assemble one.



Caveats
=======
Some things such as weapon skins seem to be packed as a pure texture
collecton pack. So you won't me able to easily get them by their mesh
UID. I don't know of any way to find those relations yet.

If Something Breaks
===================
Grab an error message, your input data (filenames, uids etc) and PM me
on xentax.com I don't promise any fast replys though.