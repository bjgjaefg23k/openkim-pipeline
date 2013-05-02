"""
Persistant Dictionary recipe from:
    http://code.activestate.com/recipes/576642-persistent-dict-with-multiple-standard-file-format/

"""

import pickle, json, csv, os, shutil, yaml
from collections import defaultdict
from kimapi import APIDict

class PersistentDict(APIDict):
    ''' Persistent dictionary with an API compatible with shelve and anydbm.

    The dict is kept in memory, so the dictionary operations run as fast as
    a regular dictionary.

    Write to disk is delayed until close or sync (similar to gdbm's fast mode).

    Input file format is automatically discovered.
    Output file format is selectable between pickle, json, and csv.
    All three serialization formats are backed by fast C implementations.

    '''

    def __init__(self, filename, flag='c', mode=None, format='json', *args, **kwargs):
        self.flag = flag                    # r=readonly, c=create, or n=new
        self.mode = mode                    # None or an octal triple like 0644
        self.format = format                # 'csv', 'json', or 'pickle'
        self.filename = filename
        if flag != 'n' and os.access(filename, os.R_OK):
            fileobj = open(filename, 'rb' if format=='pickle' else 'r')
            with fileobj:
                self.load(fileobj)
        dict.__init__(self, *args, **kwargs)
        # super(APIDict,self).__init__(*args,**kwargs)

    def sync(self):
        'Write dict to disk'
        if self.flag == 'r':
            return
        filename = self.filename
        tempname = filename + '.tmp'
        fileobj = open(tempname, 'wb' if self.format=='pickle' else 'w')
        try:
            self.dump(fileobj)
        except Exception:
            os.remove(tempname)
            raise
        finally:
            fileobj.close()
        shutil.move(tempname, self.filename)    # atomic commit
        if self.mode is not None:
            os.chmod(self.filename, self.mode)

    def close(self):
        self.sync()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def dump(self, fileobj):
        if self.format == 'csv':
            csv.writer(fileobj).writerows(self.items())
        elif self.format == 'json':
            json.dump(self, fileobj, separators=(',', ':'), indent=4)
        elif self.format == 'pickle':
            pickle.dump(dict(self), fileobj, 2)
        elif self.format == "yaml":
            yaml.dump_all(self['dict'], fileobj, default_flow_style=False, explicit_start=True)
        else:
            raise NotImplementedError('Unknown format: ' + repr(self.format))

    def load(self, fileobj):
        # try formats from most restrictive to least restrictive
        for loader in (pickle.load, json.load, csv.reader):
            fileobj.seek(0)
            try:
                return self.update(loader(fileobj))
            except Exception:
                pass
        if self.format=='yaml':
            try:
                fileobj.seek(0)
                self['dict'] = list(yaml.load_all(fileobj))
                return self
            except Exception:
                raise ValueError("Not YAML!")
        raise ValueError('File not in a supported format')

    def __str__(self):
        return json.dumps(self,separators=(',',':'),indent=4)

    def __getitem__(self, item):
        # FIXME FIXME FIXME FIXME (please....)
        if self.format == 'yaml':
            try:
                return super(PersistentDict,self).__getitem__('dict')[0].__getitem__(item)
            except KeyError:
                pass 

        value = super(PersistentDict,self).__getitem__(item)
        if isinstance(value,dict):
            return APIDict(value)
        return value


class PersistentDefaultDict(PersistentDict, defaultdict):
    """ Same as PersistentDict, but behaves as a defaultdict of dicts as well """
    def __init__(self,*args,**kwargs):
        super(PersistentDefaultDict,self).__init__(*args,**kwargs)
        self.default_factory = dict

