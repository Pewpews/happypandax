"Contains classes/functions used to encapsulate message structures"

import enum
import json
import sys
import inspect

from datetime import datetime

from happypanda.common import constants, exceptions
from happypanda.server.core import db

def finalize(msg_dict, name=constants.server_name):
    "Finalize dict message before sending"
    enc = 'utf-8'
    msg = {
        'name':name,
        'data':msg_dict
        }

    return bytes(json.dumps(msg), enc)

class CoreMessage:
    "Encapsulates return values from methods in the interface module"

    def __init__(self, key):
        self.key = key
        self._error = None

    def set_error(self, e):
        "Set an error message"
        assert isinstance(e, Error)
        self._error = e

    def data(self):
        "Implement in subclass. Must return a dict or list if intended to be serializable."
        raise NotImplementedError()

    def from_json(self, j):
        raise NotImplementedError()

    def json_friendly(self):
        "Serialize to JSON structure"
        d = self.data()
        assert isinstance(d, (dict, list)), "self.data() must return a dict or list!"
        if self._error:
            d[self._error.key] = self._error.data()
        return {self.key: d}

    def serialize(self, name=constants.server_name):
        "Serialize this object to bytes"
        return finalize(self.json_friendly(), name)

class List(CoreMessage):
    """
    Encapsulates a list of objects of the same type
    """

    def __init__(self, key, type_):
        super().__init__(key)
        self._type = type_
        self.items = []

    def append(self, item):
        assert isinstance(item, self._type), "item must be a {}".format(self._type)
        d = item.data() if isinstance(item, CoreMessage) else item
        self.items.append(d)

    def data(self):
        return self.items

    def from_json(self, j):
        return super().from_json(j)

    def serialize(self, name=constants.server_name, include_key=False):
        "Serialize this object to bytes"
        if include_key:
            f = self.json_friendly
        else:
            f = self.data
        return finalize(f(), name)


class Message(CoreMessage):
    "An arbitrary remark"

    def __init__(self, msg):
        super().__init__('msg')
        self.msg = msg

    def data(self):
        return self.msg

    def from_json(self, j):
        return super().from_json(j)

class Error(CoreMessage):
    "An error object"

    def __init__(self, error, msg):
        super().__init__('error')
        assert isinstance(msg, (Message, str))
        if isinstance(msg, str):
            msg = Message(msg)
        self.error = error
        self.msg = msg

    def data(self):
        return {'code':self.error, self.msg.key:self.msg.data()}

    def from_json(self, j):
        return super().from_json(j)

class DatabaseMessage(CoreMessage):
    "Database item mapper"

    _clsmembers = {x:y for x, y in globals().copy().items() if isinstance(y, CoreMessage)}
    _db_clsmembers = [x for x in inspect.getmembers(db, inspect.isclass) if issubclass(x[1], db.Base)]

    def __init__(self, key, db_item):
        super().__init__(key)
        assert isinstance(db_item, db.Base)
        assert db.is_instanced(db_item), "must be instanced database object"
        self.item = db_item

    def data(self, load_values=False, load_collections=False):
        """
        Params:
            load_values -- Queries database for unloaded values
            load_collections -- Queries database to fetch all items in a collection
        """
        self._check_link()
        gattribs = db.table_attribs(self.item, not load_values)
        return {x: self._unpack(x, gattribs[x], load_collections) for x in gattribs}

    def json_friendly(self, load_values=False, load_collections=False):
        """Serialize to JSON structure
        Params:
            load_values -- Queries database for unloaded values
            load_collections -- Queries database to fetch all items in a collection
        """
        d = self.data(load_values, load_collections)
        assert isinstance(d, dict), "self.data() must return a dict!"
        if self._error:
            d[self._error.key] = self._error.data()
        return {self.key: d}

    def serialize(self, load_values=False, load_collections=False):
        """Serialize this object to bytes
                Params:
            load_values -- Queries database for unloaded values
            load_collections -- Queries database to fetch all items in a collection
        """
        return finalize(self.json_friendly(load_values, load_collections))

    def _unpack(self, name, attrib, load_collections):
        "Helper method to unpack SQLalchemy objects"
        if attrib is None:
            return

        # beware lots of recursion
        if db.is_instanced(attrib):
            msg_obj = None

            exclude = (db.NameMixin.__name__,)

            for cls_name, cls_obj in self._db_clsmembers:
                if not cls_name in exclude:
                    if isinstance(attrib, cls_obj):
                        if cls_name == 'GalleryUrl':
                            print(self._clsmembers)
                        if cls_name in self._clsmembers:
                            msg_obj = self._clsmembers[cls_name](attrib)
                            break
            
            if not msg_obj:
                if isinstance(attrib, db.NameMixin):
                    msg_obj = NameMixin(name, attrib)
                else:
                    raise NotImplementedError("Message encapsulation for this database object does not exist ({})".format(type(attrib)))

            return msg_obj.data() if msg_obj else None

        elif db.is_list(attrib) or isinstance(attrib, list):
            return [self._unpack(name, x, load_collections) for x in attrib]

        elif db.is_query(attrib):
            if load_collections:
                return [self._unpack(name, x, load_collections) for x in attrib.all()]
            else:
                return []

        elif isinstance(attrib, enum.Enum):
            return attrib.name

        elif isinstance(attrib, datetime):
            return attrib.timestamp()

        elif isinstance(attrib, (bool, int, str)):
            return attrib
        else:
            raise NotImplementedError("Unpacking method for this attribute does not exist ({})".format(type(attrib)))

    def _check_link(self):
        if not self.item:
            raise exceptions.CoreError("This object has no linked database item")

class Gallery(DatabaseMessage):
    "Encapsulates database gallery object"

    def __init__(self, db_gallery):
        assert isinstance(db_gallery, db.Gallery)
        super().__init__('gallery', db_gallery)

    def from_json(self, j):
        return super().from_json(j)

class Artist(DatabaseMessage):
    "Encapsulates database artist object"

    def __init__(self, db_item):
        assert isinstance(db_item, db.Artist)
        super().__init__('artist', db_item)

    def from_json(self, j):
        return super().from_json(j)

class Collection(DatabaseMessage):
    "Encapsulates database collection object"

    def __init__(self, db_item):
        assert isinstance(db_item, db.Collection)
        super().__init__('collection', db_item)

class NameMixin(DatabaseMessage):
    "Encapsulates database namemixin object"

    def __init__(self, name, db_item):
        assert isinstance(db_item, db.NameMixin)
        super().__init__(name, db_item)

    def from_json(self, j):
        return super().from_json(j)

class Profile(DatabaseMessage):
    "Encapsulates database profile object"

    def __init__(self, db_item):
        assert isinstance(db_item, db.Profile)
        super().__init__('profile', db_item)

    def from_json(self, j):
        return super().from_json(j)

class Page(DatabaseMessage):
    "Encapsulates database page object"

    def __init__(self, db_item):
        assert isinstance(db_item, db.Page)
        super().__init__('page', db_item)

    def from_json(self, j):
        return super().from_json(j)

class Title(DatabaseMessage):
    "Encapsulates database title object"

    def __init__(self, db_item):
        assert isinstance(db_item, db.Title)
        super().__init__('title', db_item)

    def from_json(self, j):
        return super().from_json(j)

class GalleryUrl(DatabaseMessage):
    "Encapsulates database galleryurl object"

    def __init__(self, db_item):
        assert isinstance(db_item, db.GalleryUrl)
        super().__init__('galleryurl', db_item)

    def from_json(self, j):
        return super().from_json(j)

class GalleryList(DatabaseMessage):
    "Encapsulates database gallerylist object"

    def __init__(self, db_item):
        assert isinstance(db_item, db.GalleryList)
        super().__init__('gallerylist', db_item)

    def from_json(self, j):
        return super().from_json(j)

class Function(CoreMessage):
    "A function message"

    def __init__(self, fname, data = None):
        super().__init__('function')
        assert isinstance(fname, str)
        self.name = fname
        self.set_data(data)

    def set_data(self, d):
        ""
        assert isinstance(d, (CoreMessage, None))
        self._data = d

    def data(self):
        assert self._data, "No data set"
        return {'fname':self.name, 'data':self._data.data()}

    def from_json(self, j):
        return super().from_json(j)

