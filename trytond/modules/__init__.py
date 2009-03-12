#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.backend import Database
import os, sys, imp
import itertools
from sets import Set
from trytond.config import CONFIG
import trytond.tools as tools
import zipfile
import zipimport
import traceback
import logging

OPJ = os.path.join
MODULES_PATH = os.path.dirname(__file__)
sys.path.insert(1, MODULES_PATH)

MODULES = []

EGG_MODULES = {}
try:
    import pkg_resources
    for ep in pkg_resources.iter_entry_points('trytond.modules'):
        mod_name = ep.module_name.split('.')[-1]
        EGG_MODULES[mod_name] = ep
except ImportError:
    pass


class Graph(dict):

    def add_node(self, name, deps):
        for i in [Node(x, self) for x in deps]:
            i.add_child(name)
        if not deps:
            Node(name, self)

    def __iter__(self):
        level = 0
        done = Set(self.keys())
        while done:
            level_modules = [(name, module) for name, module in self.items() \
                    if module.depth==level]
            for name, module in level_modules:
                done.remove(name)
                yield module
            level += 1

    def __str__(self):
        res = ''
        for i in self:
            res += str(i)
            res += '\n'
        return res


class Singleton(object):

    def __new__(cls, name, graph):
        if name in graph:
            inst = graph[name]
        else:
            inst = object.__new__(cls)
            graph[name] = inst
        return inst


class Node(Singleton):

    def __init__(self, name, graph):
        super(Node, self).__init__()
        self.name = name
        self.graph = graph
        if not hasattr(self, 'datas'):
            self.datas = None
        if not hasattr(self, 'childs'):
            self.childs = []
        if not hasattr(self, 'depth'):
            self.depth = 0

    def add_child(self, name):
        node = Node(name, self.graph)
        node.depth = max(self.depth + 1, node.depth)
        if node not in self.all_childs():
            self.childs.append(node)
        for attr in ('init', 'update'):
            if hasattr(self, attr):
                setattr(node, attr, True)
        self.childs.sort(lambda x, y: cmp(x.name, y.name))

    def all_childs(self):
        res = []
        for child in self.childs:
            res.append(child)
            res += child.all_childs()
        return res

    def has_child(self, name):
        return Node(name, self.graph) in self.childs or \
                bool([c for c in self.childs if c.has_child(name)])

    def __setattr__(self, name, value):
        super(Node, self).__setattr__(name, value)
        if name in ('init', 'update'):
            for child in self.childs:
                setattr(child, name, value)
        if name == 'depth':
            for child in self.childs:
                setattr(child, name, value + 1)

    def __iter__(self):
        return itertools.chain(iter(self.childs),
                *[iter(x) for x in self.childs])

    def __str__(self):
        return self.pprint()

    def pprint(self, depth=0):
        res = '%s\n' % self.name
        for child in self.childs:
            res += '%s`-> %s' % ('    ' * depth, child.pprint(depth + 1))
        return res

def create_graph(module_list, force=None):
    if force is None:
        force = []
    graph = Graph()
    packages = []
    logger = logging.getLogger('modules')

    for module in module_list:
        tryton_file = OPJ(MODULES_PATH, module, '__tryton__.py')
        mod_path = OPJ(MODULES_PATH, module)
        if module in ('ir', 'workflow', 'res', 'webdav', 'tests'):
            root_path = os.path.dirname(os.path.dirname(__file__))
            tryton_file = OPJ(root_path, module, '__tryton__.py')
            mod_path = OPJ(root_path, module)
        elif module in EGG_MODULES:
            ep = EGG_MODULES[module]
            tryton_file = OPJ(ep.dist.location, 'trytond', 'modules', module,
                    '__tryton__.py')
            mod_path = OPJ(ep.dist.location, 'trytond', 'modules', module)
        if os.path.isfile(tryton_file) or zipfile.is_zipfile(mod_path+'.zip'):
            try:
                info = eval(tools.file_open(tryton_file, subdir='').read())
            except:
                logger.error('%s:eval file %s' % (module, tryton_file))
                raise
            packages.append((module, info.get('depends', []), info))
        elif module != 'all':
            logger.error('%s:Module not found!' % (module,))

    current, later = Set([x[0] for x in packages]), Set()
    while packages and current > later:
        package, deps, datas = packages[0]

        # if all dependencies of 'package' are already in the graph,
        # add 'package' in the graph
        if reduce(lambda x, y: x and y in graph, deps, True):
            if not package in current:
                packages.pop(0)
                continue
            later.clear()
            current.remove(package)
            graph.add_node(package, deps)
            node = Node(package, graph)
            node.datas = datas
            for kind in ('init', 'update'):
                if (package in CONFIG[kind]) \
                        or ('all' in CONFIG[kind]) \
                        or (kind in force):
                    setattr(node, kind, True)
        else:
            later.add(package)
            packages.append((package, deps, datas))
        packages.pop(0)

    for package, deps, datas in packages:
        if package not in later:
            continue
        missings = [x for x in deps if x not in graph]
        logger.error('%s:Unmet dependency %s' % (package, missings))
    return graph, packages, later

def load_module_graph(cursor, graph, pool, lang=None):
    if lang is None:
        lang = ['en_US']
    modules_todo = []
    logger = logging.getLogger('modules')

    modules = [x.name for x in graph]
    cursor.execute('SELECT name, state FROM ir_module_module ' \
            'WHERE name in (' + ','.join(['%s' for x in modules]) + ')',
            modules)
    module2state = {}
    for name, state in cursor.fetchall():
        module2state[name] = state

    for package in graph:
        module = package.name
        if module not in MODULES:
            continue
        logger.info(module)
        sys.stdout.flush()
        objects = pool.instanciate(module)
        package_state = module2state.get(module, 'uninstalled')
        idref = {}
        if hasattr(package, 'init') \
                or hasattr(package, 'update') \
                or (package_state in ('to install', 'to upgrade')):

            for type in objects.keys():
                for obj in objects[type]:
                    logger.info('%s:init %s' % (module, obj._name))
                    obj.init(cursor, module)

            #Instanciate a new parser for the package:
            tryton_parser = tools.TrytondXmlHandler(
                cursor=cursor,
                pool=pool,
                module=module,)

            for filename in package.datas.get('xml', []):
                mode = 'update'
                if hasattr(package, 'init') or package_state == 'to install':
                    mode = 'init'
                logger.info('%s:loading %s' % (module, filename))
                ext = os.path.splitext(filename)[1]
                if ext == '.sql':
                    if mode == 'init':
                        queries = tools.file_open(OPJ(module,
                            filename)).read().split(';')
                        for query in queries:
                            new_query = ' '.join(query.split())
                            if new_query:
                                cursor.execute(new_query)
                else:
                    # Feed the parser with xml content:
                    tryton_parser.parse_xmlstream(
                        tools.file_open(OPJ(module, filename)))

            modules_todo.append((module, list(tryton_parser.to_delete)))

            for filename in package.datas.get('translation', []):
                lang2 = os.path.splitext(filename)[0]
                if lang2 not in lang:
                    continue
                try:
                    trans_file = tools.file_open(OPJ(module, filename))
                except IOError:
                    logger.error('%s:file %s not found!' % (module, filename))
                    continue
                logger.info('%s:loading %s' % (module, filename))
                translation_obj = pool.get('ir.translation')
                translation_obj.translation_import(cursor, 0, lang2, module,
                                                   trans_file)

            cursor.execute("UPDATE ir_module_module SET state = 'installed' " \
                    "WHERE name = %s", (package.name,))
            module2state[package.name] = 'installed'

        # Create missing reports
        from trytond.report import Report
        report_obj = pool.get('ir.action.report')
        report_ids = report_obj.search(cursor, 0, [
            ('module', '=', module),
            ])
        report_names = pool.object_name_list(type='report')
        for report in report_obj.browse(cursor, 0, report_ids):
            report_name = report.report_name
            if report_name not in report_names:
                report = object.__new__(Report)
                report._name = report_name
                pool.add(report, type='report')
                report.__init__()

        cursor.commit()

    # Vacuum :
    while modules_todo:
        (module, to_delete) = modules_todo.pop()
        tools.post_import(cursor, pool, module, to_delete)


    cursor.commit()

def get_module_list():
    module_list = set()
    if os.path.exists(MODULES_PATH) and os.path.isdir(MODULES_PATH):
        for file in os.listdir(MODULES_PATH):
            if os.path.isdir(OPJ(MODULES_PATH, file)):
                module_list.add(file)
            elif file[-4:] == '.zip':
                module_list.add(file[-4:])
    for ep in pkg_resources.iter_entry_points('trytond.modules'):
         mod_name = ep.module_name.split('.')[-1]
         module_list.add(mod_name)
    module_list.add('ir')
    module_list.add('workflow')
    module_list.add('res')
    module_list.add('webdav')
    module_list.add('tests')
    return list(module_list)

def register_classes():
    import trytond.ir
    import trytond.workflow
    import trytond.res
    import trytond.webdav
    import trytond.tests

    logger = logging.getLogger('modules')

    for package in create_graph(get_module_list())[0]:
        module = package.name
        logger.info('%s:registering classes' % module)

        if module in ('ir', 'workflow', 'res', 'webdav', 'tests'):
            MODULES.append(module)
            continue

        if os.path.isfile(OPJ(MODULES_PATH, module + '.zip')):
            mod_path = OPJ(MODULES_PATH, module + '.zip')
            try:
                zimp = zipimport.zipimporter(mod_path)
                zimp.load_module(module)
            except zipimport.ZipImportError:
                tb_s = ''
                for line in traceback.format_exception(*sys.exc_info()):
                    try:
                        line = line.encode('utf-8', 'ignore')
                    except:
                        continue
                    tb_s += line
                for path in sys.path:
                    tb_s = tb_s.replace(path, '')
                if CONFIG['debug_mode']:
                    import pdb
                    traceb = sys.exc_info()[2]
                    pdb.post_mortem(traceb)
                logger.error('Couldn\'t import module %s:\n%s' % (module, tb_s))
                break
        elif os.path.isdir(OPJ(MODULES_PATH, module)):
            try:
                mod_file, pathname, description = imp.find_module(module,
                        [MODULES_PATH])
                try:
                    imp.load_module(module, mod_file, pathname, description)
                finally:
                    if mod_file is not None:
                        mod_file.close()
            except ImportError:
                tb_s = ''
                for line in traceback.format_exception(*sys.exc_info()):
                    try:
                        line = line.encode('utf-8', 'ignore')
                    except:
                        continue
                    tb_s += line
                for path in sys.path:
                    tb_s = tb_s.replace(path, '')
                if CONFIG['debug_mode']:
                    import pdb
                    traceb = sys.exc_info()[2]
                    pdb.post_mortem(traceb)
                logger.error('Couldn\'t import module %s:\n%s' % (module, tb_s))
                break
        elif module in EGG_MODULES:
            ep = EGG_MODULES[module]
            mod_path = os.path.join(ep.dist.location,
                    *ep.module_name.split('.')[:-1])
            mod_file, pathname, description = imp.find_module(module,
                    [mod_path])
            try:
                imp.load_module(module, mod_file, pathname, description)
            finally:
                if mod_file is not None:
                    mod_file.close()
        else:
            logger.error('Couldn\'t find module %s' % module)
            break
        MODULES.append(module)

def load_modules(database_name, pool, update=False, lang=None):
    res = True
    database = Database(database_name).connect()
    cursor = database.cursor()
    try:
        force = []
        if update:
            if 'all' in CONFIG['init']:
                cursor.execute("SELECT name FROM ir_module_module")
            else:
                cursor.execute("SELECT name FROM ir_module_module " \
                        "WHERE state IN ('installed', 'to install', " \
                            "'to upgrade', 'to remove')")
        else:
            cursor.execute("SELECT name FROM ir_module_module " \
                    "WHERE state IN ('installed', 'to upgrade', 'to remove')")
        module_list = [name for (name,) in cursor.fetchall()]
        if update:
            for module in CONFIG['init'].keys():
                if CONFIG['init'][module]:
                    module_list.append(module)
            for module in CONFIG['update'].keys():
                if CONFIG['update'][module]:
                    module_list.append(module)
        graph = create_graph(module_list, force)[0]

        try:
            load_module_graph(cursor, graph, pool, lang)
        except:
            cursor.rollback()
            raise

        if update:
            cursor.execute("SELECT name FROM ir_module_module " \
                    "WHERE state IN ('to remove')")
            if cursor.rowcount:
                for (mod_name,) in cursor.fetchall():
                    #TODO check if ressource not updated by the user
                    cursor.execute('SELECT model, db_id FROM ir_model_data ' \
                            'WHERE module = %s ' \
                            'ORDER BY id DESC', (mod_name,))
                    for rmod, rid in cursor.fetchall():
                        pool.get(rmod).delete(cursor, 0, rid)
                    cursor.commit()
                cursor.execute("UPDATE ir_module_module SET state = %s " \
                        "WHERE state IN ('to remove')", ('uninstalled',))
                cursor.commit()
                res = False

        module_obj = pool.get('ir.module.module')
        module_obj.update_list(cursor, 0)
        cursor.commit()
    finally:
        cursor.close()
    return res
