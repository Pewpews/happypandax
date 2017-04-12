﻿import sys, os, datetime, sqlite3, copy
from happypanda.server.core import db, galleryio

GALLERY_LISTS = []

def chapter_map(row, chapter):
    assert isinstance(chapter, Chapter)
    chapter.title = row['chapter_title']
    chapter.path = bytes.decode(row['chapter_path'])
    chapter.in_archive = row['in_archive']
    chapter.pages = row['pages']
    return chapter

def gallery_map(row, gallery, chapters=True, tags=True, hashes=True):
    gallery.title = row['title']
    gallery.artist = row['artist']
    gallery.profile = bytes.decode(row['profile'])
    gallery.path = bytes.decode(row['series_path'])
    gallery.is_archive = row['is_archive']
    try:
        gallery.path_in_archive = bytes.decode(row['path_in_archive'])
    except TypeError:
        pass
    gallery.info = row['info']
    gallery.language = row['language']
    gallery.rating = row['rating']
    gallery.status = row['status']
    gallery.type = row['type']
    gallery.fav = row['fav']

    def convert_date(date_str):
        #2015-10-25 21:44:38
        if date_str and date_str != 'None':
            return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

    gallery.pub_date = convert_date(row['pub_date'])
    gallery.last_read = convert_date(row['last_read'])
    gallery.date_added = convert_date(row['date_added'])
    gallery.times_read = row['times_read']
    gallery._db_v = row['db_v']
    gallery.exed = row['exed']
    gallery.view = row['view']
    try:
        gallery.link = bytes.decode(row['link'])
    except TypeError:
        gallery.link = row['link']

    if chapters:
        gallery.chapters = ChapterDB.get_chapters_for_gallery(gallery.id)

    if tags:
        gallery.tags = TagDB.get_gallery_tags(gallery.id)
    
    if hashes:
        gallery.hashes = HashDB.get_gallery_hashes(gallery.id)

    gallery.set_defaults()
    return gallery

class DBBase:
    "The base DB class. _DB_CONN should be set at runtime on startup"
    _DB_CONN = None
    _AUTO_COMMIT = True
    _STATE = {'active':False}

    def __init__(self, **kwargs):
        pass

    @classmethod
    def begin(cls):
        "Useful when modifying for a large amount of data"
        if not cls._STATE['active']:
            cls._AUTO_COMMIT = False
            cls.execute(cls, "BEGIN TRANSACTION")
            cls._STATE['active'] = True
        #print("STARTED DB OPTIMIZE")

    @classmethod
    def end(cls):
        "Called to commit and end transaction"
        if cls._STATE['active']:
            try:
                cls.execute(cls, "COMMIT")
            except sqlite3.OperationalError:
                pass
            cls._AUTO_COMMIT = True
            cls._STATE['active'] = False
        #print("ENDED DB OPTIMIZE")

    def execute(self, *args):
        "Same as cursor.execute"
        if self._AUTO_COMMIT:
            try:
                with self._DB_CONN:
                    return self._DB_CONN.execute(*args)
            except sqlite3.InterfaceError:
                    return self._DB_CONN.execute(*args)

        else:
            return self._DB_CONN.execute(*args)
    
    def commit(self):
        self._DB_CONN.commit()

    @classmethod
    def analyze(cls):
        cls._DB_CONN.execute('ANALYZE')

    @classmethod
    def close(cls):
        cls._DB_CONN.close()

class GalleryDB(DBBase):
    """
    Provides the following s methods:
        rebuild_thumb -> Rebuilds gallery thumbnail
        rebuild_galleries -> Rebuilds the galleries in DB
        modify_gallery -> Modifies gallery with given gallery id
        get_all_gallery -> returns a list of all gallery (<Gallery> class) currently in DB
        get_gallery_by_path -> Returns gallery with given path
        get_gallery_by_id -> Returns gallery with given id
        add_gallery -> adds gallery into db
        set_gallery_title -> changes gallery title
        gallery_count -> returns amount of gallery (can be used for indexing)
        del_gallery -> deletes the gallery with the given id recursively
        check_exists -> Checks if provided string exists
        clear_thumb -> Deletes a thumbnail
        clear_thumb_dir -> Dletes everything in the thumbnail directory
    """
    def __init__(self):
        raise Exception("GalleryDB should not be instantiated")

    @classmethod
    def get_all_gallery(cls, chapters=True, tags=True, hashes=True):
        """
        Careful, might crash with very large libraries i think...
        Returns a list of all galleries (<Gallery> class) currently in DB
        """
        cursor = cls.execute(cls, 'SELECT * FROM series')
        all_gallery = cursor.fetchall()
        return GalleryDB.gen_galleries(all_gallery, chapters, tags, hashes)

    @staticmethod
    def gen_galleries(gallery_dict, chapters=True, tags=True, hashes=True):
        """
        Map galleries fetched from DB
        """
        gallery_list = []
        for gallery_row in gallery_dict:
            gallery = Gallery()
            gallery.id = gallery_row['series_id']
            gallery = gallery_map(gallery_row, gallery, chapters, tags, hashes)
            if not os.path.exists(gallery.path):
                gallery.dead_link = True
            ListDB.query_gallery(gallery)
            gallery_list.append(gallery)

        return gallery_list

    @classmethod
    def gallery_count(cls):
        """
        Returns the amount of galleries in db.
        """
        cursor = cls.execute(cls, "SELECT count(*) AS 'size' FROM series")
        return cursor.fetchone()['size']

class ChapterDB(DBBase):
    """
    Provides the following database methods:
        update_chapter -> Updates an existing chapter in DB
        add_chapter -> adds chapter into db
        add_chapter_raw -> links chapter to the given seires id, and adds into db
        get_chapters_for_gallery -> returns a dict with chapters linked to the given series_id
        get_chapter-> returns a dict with chapter matching the given chapter_number
        get_chapter_id -> returns id of the chapter number
        chapter_size -> returns amount of manga (can be used for indexing)
        del_all_chapters <- Deletes all chapters with the given series_id
        del_chapter <- Deletes chapter with the given number from gallery
    """

    def __init__(self):
        raise Exception("ChapterDB should not be instantiated")


    @classmethod
    def get_chapters_for_gallery(cls, series_id):
        """
        Returns a ChaptersContainer of chapters matching the received series_id
        """
        assert isinstance(series_id, int), "Please provide a valid gallery ID"
        cursor = cls.execute(cls, 'SELECT * FROM chapters WHERE series_id=?', (series_id,))
        rows = cursor.fetchall()
        chapters = ChaptersContainer()

        for row in rows:
            chap = chapters.create_chapter(row['chapter_number'])
            chapter_map(row, chap)
        return chapters

class HashDB(DBBase):
    """
    Contains the following methods:

    find_gallery -> returns galleries which matches the given list of hashes
    get_gallery_hashes -> returns all hashes with the given gallery id in a list
    get_gallery_hash -> returns hash of chapter specified. If page is specified, returns hash of chapter page
    gen_gallery_hashes <- generates hashes for gallery's chapters and inserts them to db
    rebuild_gallery_hashes <- inserts hashes into DB only if it doesnt already exist
    """
    @classmethod
    def get_gallery_hashes(cls, gallery_id):
        "Returns all hashes with the given gallery id in a list"
        cursor = cls.execute(cls, 'SELECT hash FROM hashes WHERE series_id=?',
                (gallery_id,))
        hashes = []
        try:
            for row in cursor.fetchall():
                hashes.append(row['hash'])
        except IndexError:
            return []
        return hashes


class TagDB(DBBase):
    """
    Tags are returned in a dict where {"namespace":["tag1","tag2"]}
    The namespace "default" will be used for tags without namespaces.

    Provides the following methods:
    del_tags <- Deletes the tags with corresponding tag_ids from DB
    del_gallery_tags_mapping <- Deletes the tags and gallery mappings with corresponding series_ids from DB
    get_gallery_tags -> Returns all tags and namespaces found for the given series_id;
    get_tag_gallery -> Returns all galleries with the given tag
    get_ns_tags -> "Returns a dict with namespace as key and list of tags as value"
    get_ns_tags_to_gallery -> Returns all galleries linked to the namespace tags. Receives a dict like this: {"namespace":["tag1","tag2"]}
    get_tags_from_namespace -> Returns all galleries linked to the namespace
    add_tags <- Adds the given dict_of_tags to the given series_id
    modify_tags <- Modifies the given tags
    get_all_tags -> Returns all tags in database
    get_all_ns -> Returns all namespaces in database
    """

    def __init__(self):
        raise Exception("TagsDB should not be instantiated")

    @classmethod
    def get_gallery_tags(cls, series_id):
        "Returns all tags and namespaces found for the given series_id"
        if not isinstance(series_id, int):
            return {}
        cursor = cls.execute(cls, 'SELECT tags_mappings_id FROM series_tags_map WHERE series_id=?',
                (series_id,))
        tags = {}
        result = cursor.fetchall()
        for tag_map_row in result: # iterate all tag_mappings_ids
            try:
                if not tag_map_row:
                    continue
                # get tag and namespace
                c = cls.execute(cls, 'SELECT namespace_id, tag_id FROM tags_mappings WHERE tags_mappings_id=?',
                  (tag_map_row['tags_mappings_id'],))
                for row in c.fetchall(): # iterate all rows
                    # get namespace
                    c = cls.execute(cls, 'SELECT namespace FROM namespaces WHERE namespace_id=?',
                        (row['namespace_id'],))
                    try:
                        namespace = c.fetchone()['namespace']
                    except TypeError:
                        continue

                    # get tag
                    c = cls.execute(cls, 'SELECT tag FROM tags WHERE tag_id=?', (row['tag_id'],))
                    try:
                        tag = c.fetchone()['tag']
                    except TypeError:
                        continue

                    # add them to dict
                    if not namespace in tags:
                        tags[namespace] = [tag]
                    else:
                        # namespace already exists in dict
                        tags[namespace].append(tag)
            except IndexError:
                continue
        return tags

class ListDB(DBBase):
    """
    """


    @classmethod
    def init_lists(cls):
        "Creates and returns lists fetched from DB"
        lists = []
        c = cls.execute(cls, 'SELECT * FROM list')
        list_rows = c.fetchall()
        for l_row in list_rows:
            l = GalleryList(l_row['list_name'], filter=l_row['list_filter'], id=l_row['list_id'])
            if l_row['type'] == GalleryList.COLLECTION:
                l.type = GalleryList.COLLECTION
            elif l_row['type'] == GalleryList.REGULAR:
                l.type = GalleryList.REGULAR
            profile = l_row['profile']
            if profile:
                l.profile = bytes.decode(profile)
            l.enforce = bool(l_row['enforce'])
            l.regex = bool(l_row['regex'])
            l.case = bool(l_row['l_case'])
            l.strict = bool(l_row['strict'])
            lists.append(l)
            GALLERY_LISTS.append(l)

        return lists

    @classmethod
    def query_gallery(cls, gallery):
        "Maps gallery to the correct lists"

        c = cls.execute(cls, 'SELECT list_id FROM series_list_map WHERE series_id=?', (gallery.id,))
        list_rows = [x['list_id'] for x in c.fetchall()]
        for l in GALLERY_LISTS:
            if l._id in list_rows:
                l.add_gallery(gallery, False, _check_filter=False)

class GalleryList:
    """
    Provides access to lists..
    methods:
    - add_gallery <- adds a gallery of Gallery class to list
    - remove_gallery <- removes galleries matching the provided gallery id
    - clear <- removes all galleries from the list
    - galleries -> returns a list with all galleries in list
    - scan <- scans for galleries matching the listfilter and adds them to gallery
    """
    # types
    REGULAR, COLLECTION = range(2)

    def __init__(self, name, list_of_galleries=[], filter=None, id=None, _db=True):
        self._id = id # shouldnt ever be touched
        self.name = name
        self.profile = ''
        self.type = self.REGULAR
        self.filter = filter
        self.enforce = False
        self.regex = False
        self.case = False
        self.strict = False
        self._galleries = set()
        self._ids_chache = []
        self._scanning = False

    def add_gallery(self, gallery_or_list_of, _db=True, _check_filter=True):
        "add_gallery <- adds a gallery of Gallery class to list"
        assert isinstance(gallery_or_list_of, (Gallery, list))
        if isinstance(gallery_or_list_of, Gallery):
            gallery_or_list_of = [gallery_or_list_of]
        if _check_filter and self.filter and self.enforce:
            execute(self.scan, True, gallery_or_list_of)
            return
        new_galleries = []
        for gallery in gallery_or_list_of:
            self._galleries.add(gallery)
            new_galleries.append(gallery)
            self._ids_chache.append(gallery.id)
            # uses timsort algorithm so it's ok
            self._ids_chache.sort()

    def galleries(self):
        "returns a list with all galleries in list"
        return list(self._galleries)

class Gallery:
    """
    Base class for a gallery.
    Available data:
    id -> Not to be editied. Do not touch.
    title <- [list of titles] or str
    profile <- path to thumbnail
    path <- path to gallery
    artist <- str
    chapters <- {<number>:<path>}
    chapter_size <- int of number of chapters
    info <- str
    fav <- int (1 for true 0 for false)
    rating <- float
    type <- str (Manga? Doujin? Other?)
    language <- str
    status <- "unknown", "completed" or "ongoing"
    tags <- list of str
    pub_date <- date
    date_added <- date, will be defaulted to today if not specified
    last_read <- timestamp (e.g. time.time())
    times_read <- an integer telling us how many times the gallery has been opened
    hashes <- a list of hashes of the gallery's chapters
    exed <- indicator on if gallery metadata has been fetched
    valid <- a bool indicating the validity of the gallery

    Takes ownership of ChaptersContainer
    """

    def __init__(self):

        self.id = None # Will be defaulted.
        self.title = ""
        self.profile = ""
        self._path = ""
        self.path_in_archive = ""
        self.is_archive = 0
        self.artist = ""
        self._chapters = ChaptersContainer(self)
        self.info = ""
        self.fav = 0
        self.rating = 0
        self.type = ""
        self.link = ""
        self.language = ""
        self.status = ""
        self.tags = {}
        self.pub_date = None
        self.date_added = datetime.datetime.now().replace(microsecond=0)
        self.last_read = None
        self.times_read = 0
        self.valid = False
        self._db_v = None
        self.hashes = []
        self.exed = 0
        self.file_type = "folder"
        self.view = 0

        self._grid_visible = False
        self._list_view_selected = False
        self._profile_qimage = {}
        self._profile_load_status = {}
        self.dead_link = False
        self.state = 0

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, n_p):
        self._path = n_p
        _, ext = os.path.splitext(n_p)
        if ext:
            self.file_type = ext[1:].lower() # remove dot

    def set_defaults(self):
        pass

    @property
    def chapters(self):
        return self._chapters

    @chapters.setter
    def chapters(self, chp_cont):
        assert isinstance(chp_cont, ChaptersContainer)
        chp_cont.set_parent(self)
        self._chapters = chp_cont


    def __contains__(self, key):
        assert isinstance(key, Chapter), "Can only check for chapters in gallery"
        return self.chapters.__contains__(key)

    def __lt__(self, other):
        return self.id < other.id

    def __str__(self):
        s = ""
        for x in sorted(self.__dict__):
            s += "{:>20}: {:>15}\n".format(x, str(self.__dict__[x]))
        return s

class Chapter:
    """
    Base class for a chapter
    Contains following attributes:
    parent -> The ChapterContainer it belongs in
    gallery -> The Gallery it belongs to
    title -> title of chapter
    path -> path to chapter
    number -> chapter number
    pages -> chapter pages
    in_archive -> 1 if the chapter path is in an archive else 0
    """
    def __init__(self, parent, gallery, number=0, path='', pages=0, in_archive=0, title=''):
        self.parent = parent
        self.gallery = gallery
        self.title = title
        self.path = path
        self.number = number
        self.pages = pages
        self.in_archive = in_archive

    def __lt__(self, other):
        return self.number < other.number

    def __str__(self):
        s = """
        Chapter: {}
        Title: {}
        Path: {}
        Pages: {}
        in_archive: {}
        """.format(self.number, self.title, self.path, self.pages, self.in_archive)
        return s

    @property
    def next_chapter(self):
        try:
            return self.parent[self.number + 1]
        except KeyError:
            return None

    @property
    def previous_chapter(self):
        try:
            return self.parent[self.number - 1]
        except KeyError:
            return None

class ChaptersContainer:
    """
    A container for chapters.
    Acts like a list/dict of chapters.

    Iterable returns a ordered list of chapters
    Sets to gallery.chapters
    """
    def __init__(self, gallery=None):
        self.parent = None
        self._data = {}

        if gallery:
            gallery.chapters = self

    def set_parent(self, gallery):
        assert isinstance(gallery, (Gallery, None))
        self.parent = gallery
        for n in self._data:
            chap = self._data[n]
            chap.gallery = gallery

    def add_chapter(self, chp, overwrite=True, db=False):
        "Add a chapter of Chapter class to this container"
        assert isinstance(chp, Chapter), "Chapter must be an instantiated Chapter class"
        
        if not overwrite:
            try:
                _ = self._data[chp.number]
                raise Exception
            except KeyError:
                pass
        chp.gallery = self.parent
        chp.parent = self
        self[chp.number] = chp
        

        if db:
            # TODO: implement this
            pass

    def create_chapter(self, number=None):
        """
        Creates Chapter class with the next chapter number or passed number arg and adds to container
        The chapter will be returned
        """
        if number:
            chp = Chapter(self, self.parent, number=number)
            self[number] = chp
        else:
            next_number = 0
            for n in list(self._data.keys()):
                if n > next_number:
                    next_number = n
                else:
                    next_number += 1
            chp = Chapter(self, self.parent, number=next_number)
            self[next_number] = chp
        return chp

    def pages(self):
        p = 0
        for c in self:
            p += c.pages
        return p

    def get_chapter(self, number):
        return self[number]

    def get_all_chapters(self):
        return list(self._data.values())

    def count(self):
        return len(self)

    def pop(self, key, default=None):
        return self._data.pop(key, default)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        assert isinstance(key, int), "Key must be a chapter number"
        assert isinstance(value, Chapter), "Value must be an instantiated Chapter class"
        
        if value.gallery != self.parent:
            raise app_constants.ChapterWrongParentGallery
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter([self[c] for c in sorted(self._data.keys())])

    def __bool__(self):
        return bool(self._data)

    def __str__(self):
        s = ""
        for c in self:
            s += '\n' + '{}'.format(c)
        if not s:
            return '{}'
        return s

    def __contains__(self, key):
        if key.gallery == self.parent and key in [self.data[c] for c in self._data]:
            return True
        return False

def print_progress(iteration, total, prefix='', suffix='', decimals=1, bar_length=100):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        bar_length  - Optional  : character length of bar (Int)
    """
    str_format = "{0:." + str(decimals) + "f}"
    percents = str_format.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = '█' * filled_length + '-' * (bar_length - filled_length)

    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix)),

    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Provide source and destination")
        sys.exit()

    src = sys.argv[1]
    dst = sys.argv[2]

    print("Connecting to Happypanda database..")
    conn_src = sqlite3.connect(src)
    conn_src.row_factory = sqlite3.Row
    DBBase._DB_CONN = conn_src
    ListDB.init_lists()
    print("Fetching gallery lists..")
    src_galleries = GalleryDB.get_all_gallery()
    print("Fetching all galleries, chapters, tags and hashes..")
    print("Fetched galleries count:", len(src_galleries))
    print("Creating new Happypanda X database")
    engine = db.create_engine(os.path.join("sqlite:///", dst))
    db.Base.metadata.create_all(engine)
    sess = db.sessionmaker()
    sess.configure(bind=engine)
    db.initEvents(sess)
    s = sess()

    print("Converting to Happypanda X Gallery.. ")

    gallery_mixmap = {}
    dst_galleries = []
    en_lang = db.Language()
    en_lang.name = "English"
    dst_languages = {"english": en_lang}
    dst_artists = {}
    dst_gtype = {}
    dst_status = {}
    dst_namespace = {}
    dst_tag = {}
    dst_nstagmapping = {}
    dst_collections = {}
    dst_grouping = {}

    for numb, g in enumerate(src_galleries):

        galleries = []
        gallery_ns = None

        for ch in g.chapters:

            path = g.path if ch.in_archive else ch.path
            if not os.path.exists(path):
                print("Skipping {} because path doesn't exists.".format(ch.title))
                continue
            path_in_archive = ch.path

            gfs = galleryio.GalleryFS(path, path_in_archive, db.Gallery())
            gallery = gfs.get_gallery()
            try:
                if gfs.gallery_type == galleryio.utils.PathType.Directoy:
                    [gfs.gallery.pages.append(db.Page(path=x[1], number=x[0])) for x in gfs._get_folder_pages()]
                elif gfs.gallery_type == galleryio.utils.PathType.Archive:
                    [gfs.gallery.pages.append(db.Page(path=x[1], number=x[0])) for x in gfs._get_archive_pages()]
            except NotImplementedError:
                pass
            for col in copy.copy(gallery.collections):
                if col.name in dst_collections:
                    gallery.collections.remove(col)
                    gallery.collections.append(dst_collections[col.name])
                else:
                    dst_collections[col.name] = col

            if gallery_ns:
                gallery.grouping = gallery_ns
            else:
                gallery_ns = db.Grouping()
                gallery_ns.name = ch.title if ch.title else g.title
                gallery_ns = dst_grouping.get(gallery_ns.name, gallery_ns)
                dst_grouping[gallery_ns.name] = gallery_ns
                gallery_ns.galleries.append(gallery)
                if g.status:
                    gstatus = db.Status()
                    gstatus.name
                    gstatus = dst_status.get(gstatus.name, gstatus)
                    gallery_ns.status = gstatus
                    dst_status[gstatus.name] = gstatus

            gallery.number = ch.number

            lang = g.language.lower() if g.language else None
            if lang and not lang in dst_languages:
                db_lang = db.Language()
                db_lang.name = g.language
                dst_languages[lang] = db_lang
            else:
                db_lang = dst_languages['english']

            title = db.Title()
            title.name = ch.title if ch.title else g.title
            title.language = db_lang
            gallery.titles.clear()
            gallery.titles.append(title)

            if g.artist:
                artist = db.Artist()
                artist.name = g.artist
                artist = dst_artists.get(artist.name, artist)
                gallery.artists.append(artist)
                dst_artists[artist.name] = artist
            gallery.info = g.info
            gallery.fav = bool(g.fav)
            gallery.rating = g.rating
            if g.type:
                gtype = db.GalleryType()
                gtype.name = g.type
                gtype = dst_gtype.get(gtype.name, gtype)
                gallery.type = gtype
                dst_gtype[gtype.name] = gtype

            if g.link:
                gurl = db.GalleryUrl()
                gurl.url = g.link
                gallery.urls.append(gurl)

            gallery.pub_date = g.pub_date
            gallery.timestamp = g.date_added
            gallery.last_read = g.last_read
            gallery.times_read = g.times_read
            gallery.catagory = gallery.Category.Library if not g.view else gallery.Category.Inbox

            galleries.append(gallery)
            if not g.id in gallery_mixmap:
                gallery_mixmap[g.id] = []
            gallery_mixmap[g.id].append(gallery)

        # tags

        for ns in g.tags:
            n = db.Namespace()
            n.name = ns
            n = dst_namespace.get(ns, n)
            dst_namespace[ns] = n
            for tag in g.tags[ns]:
                t = db.Tag()
                t.name = tag
                t = dst_tag.get(tag, t)
                dst_tag[t.name] = t
                nstagname = ns + tag
                nstag = db.NamespaceTags(n, t)
                nstag = dst_nstagmapping.get(nstagname, nstag)
                dst_nstagmapping[nstagname] = nstag
                for ch_g in galleries:
                    ch_g.tags.append(nstag)

        # hashes

        dst_galleries.extend(galleries)

        print_progress(numb, len(src_galleries), "Progress:", bar_length=50)

    print("\nCreating gallery lists")
    dst_lists = []
    for l in GALLERY_LISTS:
        glist = db.GalleryList()
        glist.name = l.name
        glist.filter = l.filter
        glist.enforce = l.enforce
        glist.regex = l.regex
        glist.l_case = l.case
        glist.strict = l.strict
        for g in l.galleries():
            if g.id in gallery_mixmap:
                glist.galleries.extend(gallery_mixmap[g.id])

        dst_lists.append(glist)

    print("Adding languages...")
    s.add_all(dst_languages.values())
    print("Adding artists...")
    s.add_all(dst_artists.values())
    print("Adding gallery types...")
    s.add_all(dst_gtype.values())
    print("Adding gallery status...")
    s.add_all(dst_status.values())
    print("Adding gallery namespaces...")
    s.add_all(dst_namespace.values())
    print("Adding gallery tags...")
    s.add_all(dst_tag.values())
    s.add_all(dst_nstagmapping.values())
    print("Adding galleries...")
    s.add_all(dst_galleries)
    print("Adding gallery lists...")
    s.add_all(dst_lists)

    s.commit()
    print("Done!")


