"""
This module is meant to build assets data cache to be used by asset data
extractor.

By default, cache is stored in current working directory of a script,
that uses this module. IT can be overriden:
>>> SiegeLinksData(cache_dir="D:\\my\\custom\\cache")

Whenever one invokes SiegeLinksData(), it checks for cache_dir to exist.
IF it exist, this script loads cached links and other metadata used for
faster asset search. If cache folder is absent, it generates new cache.

Keep in mind, it only checks for dir existence, not it's contents. If
one creates an empy cache folder, this module will attempt to read
non-existent files in it and fail. To force cache recalculation, delete
the whole cache folder. Do it each time your game distribution updates.
You can also force cache recalculation from within the code, simply do:
>>> data = SiegeLinksData(load=False)  # skip loading obsolete data
>>> data.generate()  # build new data
"""
import r6s
import os
import pickle as pckl
import pathlib as pth

log = print


ASSET_MAGIC = 0x22ECBE63


class SiegeLinksData:
    _ASSET_UIDS_CACHE = "asset_uids.pckl"
    _ALL_LINKS_CACHE = "all_links.pckl"
    _ASSET_CHILDREN = "asset_children.pckl"
    _UIDS_INDEX = "uids_index.pckl"

    def __init__(self, forges_dir=None, cache_dir=None, load=True):
        """
        :parm str forges_dir:
            path to dir with forge and depgraphbin files
        :parm str cache_dir:
            path to cache folder to either read or generate
        :parm bool load:
            whether to read/generate cache upon instance initialization
        """
        self.FORGES_DIR = forges_dir or r6s.settings.IMPORT
        self.CACHE_DIR = cache_dir or "./cache"
        self.all_links = None
        self.asset_children = None
        self.asset_uids = None
        self.uids_index = None
        if load:
            self.reload()

    def _get_cdir(self):
        return (pth.Path.cwd() / self.CACHE_DIR).resolve()

    def _get_idir(self):
        return (pth.Path.cwd() / self.FORGES_DIR).resolve()

    def reload(self):
        cdir = self._get_cdir()
        if not cdir.is_dir():
            print("generating", print("loading", self._get_cdir()))
            # self.generate()
        else:
            self.load()

    def generate(self):
        idir = self._get_idir()
        cdir = self._get_cdir()
        log(f"Game data dir: {idir}")

        # make cache dir to store extra data for speed
        if not cdir.is_dir():
            log(f"Creating cache dir at {cdir}")
            cdir.mkdir()
        else:
            log(f"Cache dir: {cdir}")

        # make cache dir to store extra data for speed
        if not cdir.is_dir():
            log(f"Creating cache dir at {cdir}")
            cdir.mkdir()
        else:
            log(f"Cache dir: {cdir}")

        ### gather all asset uids and entry addresses
        cch_asset_uids = cdir / self._ASSET_UIDS_CACHE
        cch_uids_index = cdir / self._UIDS_INDEX
        asset_uids = []
        uids_index = {}
        log(f"Gathering asset uids:")
        for fpath in idir.glob("*.forge"):
            log(f"    {fpath.name}")
            with r6s.forge.parse(fpath) as f:
                for i, (e, n) in enumerate(zip(f.entries, f.names)):
                    if n.file_type == ASSET_MAGIC:
                        asset_uids.append(e.uid)
                    uids_index[e.uid] = {
                        "forge": fpath.name,
                        "index": i,
                        "magic": n.file_type,
                    }
                    log(f"    {i}", end="\r")
        log(f"Total amount of asset uids: {len(asset_uids)}")
        log(f"Storing uids to {cch_asset_uids}")
        with cch_asset_uids.open("bw") as w:
            pckl.dump(asset_uids, w)
        with cch_uids_index.open("bw") as w:
            pckl.dump(uids_index, w)
        log("\n\n")

        ### gather depgraph links
        cch_all_links = cdir / self._ALL_LINKS_CACHE
        all_links = r6s.forge.DepGraph()
        log("Gathering dependencies:")
        for fpath in idir.glob("*.depgraphbin"):
            log(f"    {fpath.name}")
            all_links.parse(fpath)
        log(f"Storing all links to {cch_all_links}")
        with cch_all_links.open("bw") as w:
            pckl.dump(all_links, w)
        log("\n\n")

        ### clear so it has only assets dependencies
        cch_asset_children = cdir / self._ASSET_CHILDREN
        log("Filtering assets' children:")
        total_links = len(all_links.links)
        filtered_links = []
        for i, l in enumerate(all_links.links):
            log(f"    {i:>8d} of {total_links}", end="\r")
            if l.src in asset_uids:
                filtered_links.append(l)
        asset_children = r6s.forge.DepGraph()
        asset_children.links = filtered_links
        log(f"Total amount of filtered dependencies: {len(filtered_links)}")
        log(f"Storing links to {cch_asset_children}")
        with cch_asset_children.open("bw") as w:
            pckl.dump(all_links, w)
        log("\n\n")

        self.asset_uids = asset_uids
        self.all_links = all_links
        self.asset_children = asset_children
        self.uids_index = uids_index

        log("DONE")

    def load(self):
        idir = self._get_idir()
        cdir = self._get_cdir()
        cch_asset_uids = cdir / self._ASSET_UIDS_CACHE
        cch_all_links = cdir / self._ALL_LINKS_CACHE
        cch_asset_children = cdir / self._ASSET_CHILDREN
        cch_uids_index = cdir / self._UIDS_INDEX

        with open(cch_asset_uids, "rb") as r:
            self.asset_uids = pckl.load(r)
        with open(cch_all_links, "rb") as r:
            self.all_links = pckl.load(r)
        with open(cch_asset_children, "rb") as r:
            self.asset_children = pckl.load(r)
        with open(cch_uids_index, "rb") as r:
            self.uids_index = pckl.load(r)
