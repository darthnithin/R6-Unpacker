About
=====

This module is intended for research and reverse engineering of siege's
forge archives. It is capable of ripping some types of data by itself
but the idea is that it will be the foundation for proper standalone
tools that other people are going to write. I try to write core modules
as clean as possible so it's more or less documented. I also want to
thank people who helped me along the way with some qwirks of siege's
format:
- RED_EYE
- zaramot
- Luxox

This tool is intended to be used with python >= 3.6.



Installation
============

## Option 1:
This is the one I use because I want to keep the code at hand and not
limited to a particular env.

1. place `r6s` folder and `binstream.py` into a folder of your choice
   (for example's sake let it be `D:\my_packages`)
2. navigate into `site-packages` directory of your python distribution
3. create a file named `siege.pth`, open it and write `D:\my_packages`
   in it

To read more on this mechanism, refer to
https://docs.python.org/3/library/site.html


## Option 2 (if you like to trash your site-packages dir):

Just copy `r6s` folder and `binstream.py` into your python's
`site-packages` folder.


## Option 3 (if you like to trash your code):

1. place `r6s` folder and `binstream.py` into a folder of your choice
   (for example's sake let it be `D:\my_packages`)
2. at the beginning of your python code, use this snippet
   ```python
    import sys
    sys.path.append('D:\\my_packages')
   ```

## Dependencies
### zstandard
This package needs zstandard to run, so either run
`pip install zstandard` or `conda install zstandard` depending on
whatever your package manager is.

### rawtex and texconv
I also use RawTex and texconv to convert forge data to actual textures,
so you will need those too.

- [Get RawTex](https://forum.xentax.com/viewtopic.php?f=18&t=16461)
- [Get texconv](https://github.com/microsoft/DirectXTex/releases)

Drop all files into a folder of your choice, for example `D:\tex_bin`

## Setting it all up
Open `r6s/settings.py` and edit it to fit your config.
* `tex_bin` should point to your RawTex and texconv execs (`D:\tex_bin`
            in our example case)
* `IMPORT` should point to your Siege distribution with all it's 
* `EXPORT` is rarely used and can be ignored unless you want to use it
           in your own scripts



Usage
=====

## I just want to dump some assets
I've provided a couple of scripts and a `.blend` file in `scripts`
folder. They have their own README, read it and use those.

## I want to write my code using this package
The code is written so that it's easy to get access to all main
properties that forge files store within them and so you can dump files
with just a bunch of lines.

### dumping the whole forge out
Dumps a given entry and saves each item as a file with it's UID as it's
name.

```python
import r6s

with r6s.forge.parse('filename.forge') as forge:
    for i,e,n,c in forge.files():
        # i - entry index
        # e - Entry object, contains offset, size and uid of a file
        # n - NameEntry object (old class name, not relevant anymore)
        #     contains compressed metadata (haven't cracked it yet),
        #     magic number and other less interesting stuff. Can be
        #     used for fast specific filetype search
        # c - Container. 99% of time it's a compressed file (if
        #     n.file_type != 0). It has `meta` and `file` attributes.
        #     meta is deprecated since Y5 when it was compressed and
        #     moved inside each entry's blob, just ignore it.
        with open('dump\\%s.file' % e.uid, 'rb') as outfile:
            data = r6s.forge.getdatastream(c.file, forge.reader)
            # data - a stream object that contains uncompressed and
            #         ready to use contents of a file
            outfile.write(data.read()) 
```

This is the basic version of it. If you strip comments, you will get
6 lines of code.

### getting textures out
Dumps each texture as a png into an `out_dir`.

```python
import r6s

out_dir = "D:\\folder_to_dump_textures_in"
with r6s.forge.parse('filename_texture3.forge') as forge:
    for i, e, n, c in forge.files():
        r6s.tex.savebyuid(forge, e.uid, out_dir)
        # this function builds dds and png file for a given entry
```

In case you want to access texture's metadata, use this snippet:
```python
import r6s

with r6s.forge.parse('filename_texture3.forge') as forge:
    for i, e, n, c in forge.files():
        data = r6s.forge.getdatastream(c.file, forge.reader)
        with r6s.tex.Tex(data) as tex:
            # now tex is a Tex object that holds all metadata from forge
            # texture except for actual pixel data. This is basically a
            # metadata container, just as anything else in this
            # package. But more on that below.
            print(
               'texture uid: %s, kind of w: %s, kind of h: %s' %
               (tex.header.uid, tex.w, tex.h)
            )
```



Technical details
=================

Most objects are designed to work as metadata containers. They parse
original data, gather all parameters that are reversed but skip the
actual blobs. Actual data is retrieved via dedicated functions or
methods which are custom for each module (and need standardization and
better naming). This allows for fast retrieval of analytical data and
being able to scan all forges with thousands of files in them without
suffering long reads and memory overflow.

Many objects are also designed to be executed within `with` statement.
This allows to not worry about closing file handles.

```python
# compare this
forge = r6s.forge.Forge(open('some.forge', 'rb'))
print(len(forge.entries))
forge.close()

# against this
with r6s.forge.parse('some.forge') as forge:
    print(len(forge.entries))
```

Forge files store their file handle in a `forge.reader` attribute.
`Forge.close()` is an alias of `Forge.reader.close()`. If you need to
reopen it for some reason, use `Forge.ensureopen()` (will fail if your
reader wasn't a file).

Code is pretty much self-documented so rely on that when you search for
specific functionality. I will try to provide more examples depending
on demand.



TODOs
=====
There are some areas where I need your help. I don't yet know how to
decode skin weights. I also have problems with asset files (they have
a pesky way of packing a list of structures with variable lengths, I
have never seen such serialized list so an extra pair of eyes could
help). If you feel like you can provide some input on those matters,
please, PLEASE contact me, don't feel shy.



Contact
=======

In case you have comments, suggestions, patches or valuable info on
internal format data, [please leave it in this thread.][xentax thread].

[xentax thread]: https://forum.xentax.com/viewtopic.php?f=16&t=15031