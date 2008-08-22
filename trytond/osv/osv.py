#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
"Objects Services"

from orm import ORM
from trytond.netsvc import Service, LocalService, Logger, LOG_ERROR
from trytond import pooler
import copy
import sys
from trytond.sql_db import IntegrityError
import traceback
from trytond.tools import Cache
import time
from threading import Semaphore
from trytond.config import CONFIG

MODULE_LIST = []
MODULE_CLASS_LIST = {}
CLASS_POOL = {}


class OSVService(Service):

    def __init__(self):
        self.object_name_pool = {}
        self.module_obj_list = {}
        Service.__init__(self, 'object_proxy')
        Service.join_group(self, 'web-services')
        Service.export_method(self, self.object_name_list)
        Service.export_method(self, self.exec_workflow)
        Service.export_method(self, self.execute)
        Service.export_method(self, self.execute_cr)

    def execute_cr(self, cursor, user, object_name, method, *args, **kargs):
        # TODO: check security level
        try:
            obj = pooler.get_pool(cursor.dbname).get(object_name)
            if not obj:
                raise Exception('Error',
                        'Object %s doesn\'t exist' % str(object_name))
            if method not in obj._rpc_allowed:
                raise Exception('Error',
                        'Calling method %s on object %s is not allowed' \
                                % (method, object_name))
            res = getattr(obj, method)(cursor, user, *args, **kargs)
            return res
        except Exception, exception:
            if exception.args \
                    and exception.args[0] in ('UserError',
                            'ConcurrencyException') \
                    and not CONFIG['verbose']:
                raise
            if isinstance(exception, IntegrityError) and not CONFIG['verbose']:
                raise Exception('UserError', 'Constraint Error',
                        *exception.args)
            tb_s = reduce(lambda x, y: x+y,
                    traceback.format_exception(*sys.exc_info()))
            logger = Logger()
            logger.notify_channel("web-services", LOG_ERROR,
                    'Exception in call: \n' + tb_s)
            if isinstance(exception, IntegrityError):
                raise Exception('UserError', 'Constraint Error',
                        *exception.args)
            raise

    def execute(self, dbname, user, object_name, method, *args, **kargs):
        database, pool = pooler.get_db_and_pool(dbname)
        cursor = database.cursor()
        # TODO add retry when exception for concurency update
        try:
            try:
                res = pool.execute_cr(cursor, user, object_name, method,
                        *args, **kargs)
                cursor.commit()
            except Exception:
                cursor.rollback()
                raise
        finally:
            cursor.close()
        return res

    def exec_workflow_cr(self, cursor, user, object_name, method, *args):
        wf_service = LocalService("workflow")
        try:
            wf_service.trg_validate(user, object_name, args[0], method, cursor)
        except Exception, exception:
            if exception.args \
                    and exception.args[0] in ('UserError',
                            'ConcurrencyException') \
                    and not CONFIG['verbose']:
                raise
            if isinstance(exception, IntegrityError) and not CONFIG['verbose']:
                raise Exception('UserError', 'Constraint Error',
                        *exception.args)
            tb_s = reduce(lambda x, y: x+y,
                    traceback.format_exception(*sys.exc_info()))
            logger = Logger()
            logger.notify_channel("web-services", LOG_ERROR,
                    'Exception in call: \n' + tb_s)
            if isinstance(exception, IntegrityError):
                raise Exception('UserError', 'Constraint Error',
                        *exception.args)
            raise
        return True

    def exec_workflow(self, dbname, user, object_name, method, *args):
        cursor = pooler.get_db(dbname).cursor()
        # TODO add retry when exception for concurency update
        try:
            try:
                res = self.exec_workflow_cr(cursor, user, object_name, method,
                        *args)
                cursor.commit()
            except Exception:
                cursor.rollback()
                raise
        finally:
            cursor.close()
        return res

    def object_name_list(self):
        return self.object_name_pool.keys()

    def add(self, name, object_name_inst):
        """
        adds a new obj instance to the obj pool.
        if it already existed, the instance is replaced
        """
        if self.object_name_pool.has_key(name):
            del self.object_name_pool[name]
        self.object_name_pool[name] = object_name_inst

        module = str(object_name_inst.__class__)[6:]
        module = module[:len(module)-1]
        module = module.split('.')[0][2:]
        self.module_obj_list.setdefault(module, []).append(object_name_inst)

    def get(self, name):
        return self.object_name_pool[name]

    def instanciate(self, module):
        res = []
        class_list = MODULE_CLASS_LIST.get(module, [])
        for klass in class_list:
            res.append(klass.create_instance(self, module))
        return res

osv_pool = OSVService


class OSV(ORM):

    def __new__(cls):
        for module in cls.__module__.split('.'):
            if module != 'trytond' and module != 'modules':
                break
        if not hasattr(cls, '_module'):
            cls._module = module
        MODULE_CLASS_LIST.setdefault(cls._module, []).append(cls)
        CLASS_POOL[cls._name] = cls
        if module not in MODULE_LIST:
            MODULE_LIST.append(cls._module)
        return None

    def create_instance(cls, pool, module):
        """
        try to apply inheritancy at the instanciation level and
        put objs in the pool var
        """
        if cls._name in pool.object_name_list():
            parent_class = pool.get(cls._name).__class__
            cls = type(cls._name, (cls, parent_class), {})

        obj = object.__new__(cls)
        pool.add(obj._name, obj)
        obj.pool = pool
        obj.__init__()
        return obj

    create_instance = classmethod(create_instance)

    def __init__(self):
        super(OSV, self).__init__()

osv = OSV


class Cacheable(object):

    def __init__(self):
        super(Cacheable, self).__init__()
        self._cache = {}
        self.name = self._table
        self.timestamp = None
        self.max_len = 1024
        self.timeout = 3600
        self.semaphore = Semaphore()
        Cache._cache_instance.append(self)

    def add(self, cursor, key, value):
        self.semaphore.acquire()
        try:
            self._cache.setdefault(cursor.dbname, {})

            lower = None
            if len(self._cache[cursor.dbname]) > self.max_len:
                mintime = time.time() - self.timeout
                for key2 in self._cache[cursor.dbname].keys():
                    last_time = self._cache[cursor.dbname][key2][1]
                    if mintime > last_time:
                        del self._cache[cursor.dbname][key2]
                    else:
                        if not lower or lower[1] > last_time:
                            lower = (key2, last_time)
            if len(self._cache[cursor.dbname]) > self.max_len and lower:
                del self._cache[cursor.dbname][lower[0]]

            self._cache[cursor.dbname][key] = (value, time.time())
        finally:
            self.semaphore.release()

    def invalidate(self, cursor, key):
        self.semaphore.acquire()
        try:
            del self._cache[cursor.dbname][key]
        finally:
            self.semaphore.release()

    def get(self, cursor, key):
        try:
            self.semaphore.acquire()
            try:
                res = self._cache[cursor.dbname][key][0]
            finally:
                self.semaphore.release()
            return res
        except KeyError:
            return None

    def clear(self, cursor):
        self.semaphore.acquire()
        try:
            self._cache.setdefault(cursor.dbname, {})
            self._cache[cursor.dbname].clear()
            Cache.reset(cursor.dbname, self.name)
        finally:
            self.semaphore.release()
