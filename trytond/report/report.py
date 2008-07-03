#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
"Report"
from trytond.netsvc import Service, service_exist, Logger, LOG_ERROR
from trytond import pooler
import copy
import xml
from xml import dom
from xml.dom import minidom
from trytond.osv import ExceptORM, ExceptOSV, OSV
import sys
import base64
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import zipfile
import locale
import time
import os
import datetime
import md5
from _strptime import LocaleTime

MODULE_LIST = []
MODULE_CLASS_LIST = {}
CLASS_POOL = {}
_LOCALE2WIN32 = {
    'af_ZA': 'Afrikaans',
    'ar_AE': 'Arabic_UAE',
    'ar_BH': 'Arabic_Bahrain',
    'ar_DZ': 'Arabic_Algeria',
    'ar_EG': 'Arabic_Egypt',
    'ar_IQ': 'Arabic_Iraq',
    'ar_JO': 'Arabic_Jordan',
    'ar_KW': 'Arabic_Kuwait',
    'ar_LB': 'Arabic_Lebanon',
    'ar_LY': 'Arabic_Libya',
    'ar_MA': 'Arabic_Morocco',
    'ar_OM': 'Arabic_Oman',
    'ar_QA': 'Arabic_Qatar',
    'ar_SA': 'Arabic_Saudi_Arabia',
    'ar_SY': 'Arabic_Syria',
    'ar_TN': 'Arabic_Tunisia',
    'ar_YE': 'Arabic_Yemen',
    'az-Cyrl-AZ': 'Azeri_Cyrillic',
    'az-Latn-AZ': 'Azeri_Latin',
    'be_BY': 'Belarusian',
    'bg_BG': 'Bulgarian',
    'bs_BA': 'Serbian (Latin)',
    'ca_ES': 'Catalan',
    'cs_CZ': 'Czech',
    'da_DK': 'Danish',
    'de_AT': 'German_Austrian',
    'de_CH': 'German_Swiss',
    'de_DE': 'German_Standard',
    'de_LI': 'German_Liechtenstein',
    'de_LU': 'German_Luxembourg',
    'el_GR': 'Greek_Greece',
    'en_AU': 'English_Australian',
    'en_BZ': 'English_Belize',
    'en_CA': 'English_Canadian',
    'en_IE': 'English_Irish',
    'en_JM': 'English_Jamaica',
    'en_TT': 'English_Trinidad',
    'en_US': 'English_USA',
    'en_ZW': 'English_Zimbabwe',
    'es_AR': 'Spanish_Argentina',
    'es_BO': 'Spanish_Bolivia',
    'es_CL': 'Spanish_Chile',
    'es_CO': 'Spanish_Colombia',
    'es_CR': 'Spanish_Costa_Rica',
    'es_DO': 'Spanish_Dominican_Republic',
    'es_EC': 'Spanish_Ecuador',
    'es_ES': 'Spanish_Modern_Sort',
    'es_ES_tradnl': 'Spanish_Traditional_Sort',
    'es_GT': 'Spanish_Guatemala',
    'es_HN': 'Spanish_Honduras',
    'es_MX': 'Spanish_Mexican',
    'es_NI': 'Spanish_Nicaragua',
    'es_PA': 'Spanish_Panama',
    'es_PE': 'Spanish_Peru',
    'es_PR': 'Spanish_Puerto_Rico',
    'es_PY': 'Spanish_Paraguay',
    'es_SV': 'Spanish_El_Salvador',
    'es_UY': 'Spanish_Uruguay',
    'es_VE': 'Spanish_Venezuela',
    'et_EE': 'Estonian_Estonia',
    'eu_ES': 'Basque',
    'fa_IR': 'Farsi_Iran',
    'fi_FI': 'Finnish_Finland',
    'fr_BE': 'French_Belgian',
    'fr_CA': 'French_Canadian',
    'fr_CH': 'French_Swiss',
    'fr_FR': 'French_Standard',
    'fr_LU': 'French_Luxembourg',
    'fr_MC': 'French_Monaco',
    'ga': 'Scottish Gaelic',
    'gl_ES': 'Galician_Spain',
    'gu': 'Gujarati_India',
    'he_IL': 'Hebrew',
    'he_IL': 'Hebrew_Israel',
    'hi_IN': 'Hindi',
    'hi_IN': 'Hindi',
    'hr_HR': 'Croatian',
    'hu_HU': 'Hungarian',
    'hu': 'Hungarian_Hungary',
    'hy_AM': 'Armenian',
    'id_ID': 'Indonesian',
    'is_IS': 'Icelandic',
    'it_CH': 'Italian_Swiss',
    'it_IT': 'Italian_Standard',
    'ja_JP': 'Japanese',
    'ka_GE': 'Georgian_Georgia',
    'kk_KZ': 'Kazakh',
    'km_KH': 'Khmer',
    'kn_IN': 'Kannada',
    'ko_IN': 'Konkani',
    'ko_KR': 'Korean',
    'lo_LA': 'Lao_Laos',
    'lt_LT': 'Lithuanian',
    'lv_LV': 'Latvian',
    'mi_NZ': 'Maori',
    'mi_NZ': 'Maori',
    'mi_NZ': 'Maori',
    'mk_MK': 'Macedonian',
    'ml_IN': 'Malayalam_India',
    'mn': 'Cyrillic_Mongolian',
    'mr_IN': 'Marathi',
    'ms_BN': 'Malay_Brunei_Darussalam',
    'ms_MY': 'Malay_Malaysia',
    'nb_NO': 'Norwegian_Bokmal',
    'nl_BE': 'Dutch_Belgian',
    'nl_NL': 'Dutch_Standard',
    'nn_NO': 'Norwegian-Nynorsk',
    'ph_PH': 'Filipino_Philippines',
    'pl_PL': 'Polish',
    'pt_BR': 'Portuguese_Brazil',
    'pt_PT': 'Portuguese_Standard',
    'ro_RO': 'Romanian',
    'ru_RU': 'Russian',
    'sa_IN': 'Sanskrit',
    'sk_SK': 'Slovak',
    'sl_SI': 'Slovenian',
    'sq_AL': 'Albanian',
    'sr_CS': 'Serbian_Latin',
    'sv_FI': 'Swedish_Finland',
    'sv_SE': 'Swedish',
    'sw_KE': 'Swahili',
    'ta_IN': 'Tamil',
    'th_TH': 'Thai',
    'tr_IN': 'Urdu',
    'tr_TR': 'Turkish',
    'tt_RU': 'Tatar',
    'uk_UA': 'Ukrainian',
    'uz-Cyrl_UZ': 'Uzbek_Cyrillic',
    'uz-Latn_UZ': 'Uzbek_Latin',
    'vi_VN': 'Vietnamese',
    'zh_CN': 'Chinese_PRC',
    'zh_HK': 'Chinese_Hong_Kong',
    'zh_MO': 'Chinese_Macau',
    'zh_SG': 'Chinese_Singapore',
    'zh_TW': 'Chinese_Taiwan',
}



class ReportService(Service):

    def __init__(self):
        self.object_name_pool = {}
        self.module_obj_list = {}
        Service.__init__(self, 'report_proxy')
        Service.join_group(self, 'web-services')
        Service.export_method(self, self.execute)

    def execute_cr(self, cursor, user, report_name, ids, datas, context=None):
        try:
            report = pooler.get_pool_report(cursor.dbname).get(report_name)
            if not report:
                report = Report.create_instance(self, 'report', pooler.get_pool(cursor.dbname))
                report._name = report_name
                self.add(report._name, report)
            res = report.execute(cursor, user, ids, datas, context)
            return res
        except ExceptORM, inst:
            self.abort_response(inst.name, 'warning', inst.value)
        except ExceptOSV, inst:
            self.abort_response(inst.name, inst.exc_type, inst.value)
        except:
            import traceback
            tb_s = reduce(lambda x, y: x+y,
                    traceback.format_exception(*sys.exc_info()))
            Logger().notify_channel("web-services", LOG_ERROR,
                    'Exception in call: ' + tb_s)
            raise

    def execute(self, dbname, user, report_name, ids, datas, context=None):
        cursor = pooler.get_db(dbname).cursor()
        pool = pooler.get_pool_report(dbname)
        try:
            try:
                res = pool.execute_cr(cursor, user, report_name, ids, datas, context)
                cursor.commit()
            except Exception:
                cursor.rollback()
                raise
        finally:
            cursor.close()
        return res

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
        return self.object_name_pool.get(name, None)

    def instanciate(self, module, pool_obj):
        res = []
        class_list = MODULE_CLASS_LIST.get(module, [])
        for klass in class_list:
            res.append(klass.create_instance(self, module, pool_obj))
        return res

PARENTS = {
    'table-row': 1,
    'list-item': 1,
    'body': 0,
    'section': 0,
}


class Report(object):
    _name = ""

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

    def create_instance(cls, pool, module, pool_obj):
        """
        try to apply inheritancy at the instanciation level and
        put objs in the pool var
        """
        if pool.get(cls._name):
            parent_class = pool.get(cls._name).__class__
            cls = type(cls._name, (cls, parent_class), {})

        obj = object.__new__(cls)
        obj.__init__(pool, pool_obj)
        return obj

    create_instance = classmethod(create_instance)

    def __init__(self, pool, pool_obj):
        if self._name:
            pool.add(self._name, self)
        self.pool = pool_obj
        super(Report, self).__init__()

    def execute(self, cursor, user, ids, datas, context=None):
        if context is None:
            context = {}
        action_report_obj = self.pool.get('ir.action.report')
        action_report_ids = action_report_obj.search(cursor, user, [
            ('report_name', '=', self._name)
            ], context=context)
        if not action_report_ids:
            raise ExceptOSV('Error', 'Report (%s) not find!' % self._name)
        action_report = action_report_obj.browse(cursor, user,
                action_report_ids[0], context=context)
        objects = self._get_objects(cursor, user, ids, action_report.model,
                datas, context)
        type, data = self.parse(cursor, user, action_report,
                objects, datas, context)
        return (type, base64.encodestring(data), action_report.direct_print)

    def _get_objects(self, cursor, user, ids, model, datas, context):
        model_obj = self.pool.get(model)
        context = context.copy()
        if 'language' in context:
            del context['language']
        return model_obj.browse(cursor, user, ids, context=context)

    def parse(self, cursor, user, report, objects, datas, context):
        localcontext = {}
        localcontext['datas'] = datas
        localcontext['objects'] = objects
        localcontext['user'] = self.pool.get('res.user').\
                browse(cursor, user, user)
        localcontext['_language_cache'] = {}
        localcontext.update(context)
        if not report.report_content:
            raise ExceptOSV('Error', 'Missing report file!')
        #cStringIO difference:
        #calling StringIO() with a string parameter creates a read-only object
        content_io = StringIO.StringIO()
        content_io.write(report.report_content)
        content_z = zipfile.ZipFile(content_io, mode='r')
        localcontext['content_z'] = content_z
        content_xml = content_z.read('content.xml')
        dom = xml.dom.minidom.parseString(content_xml)
        node = dom.documentElement
        self._parse_node(cursor, user, node, localcontext, context)

        style_z = zipfile.ZipFile(content_io, mode='r')
        style_xml = content_z.read('styles.xml')
        style_z.close()
        dom_style = xml.dom.minidom.parseString(style_xml)
        node_style = dom_style.documentElement
        self._parse_node(cursor, user, node_style, localcontext, context)
        content_z.close()

        pictures = []
        if report.style_content:
            #cStringIO difference:
            #calling StringIO() with a string parameter creates a read-only object
            style2_io = StringIO.StringIO()
            style2_io.write(report.style_content)
            style2_z = zipfile.ZipFile(style2_io, mode='r')
            style2_xml = style2_z.read('styles.xml')
            for file in style2_z.namelist():
                if file.startswith('Pictures'):
                    picture = style2_z.read(file)
                    pictures.append((file, picture))
            style2_z.close()
            style2_io.close()
            dom_style2 = xml.dom.minidom.parseString(style2_xml)
            node_style2 = dom_style2.documentElement
            self._parse_node(cursor, user, node_style2, localcontext, context)
            style_header_node2 = self.find(node_style2, 'master-styles')
            style_header_node = self.find(node_style, 'master-styles')
            style_header_node.parentNode.replaceChild(style_header_node2,
                    style_header_node)
            style_header_node2 = self.find(node_style2, 'automatic-styles')
            style_header_node = self.find(node_style, 'automatic-styles')
            style_header_node.parentNode.replaceChild(style_header_node2,
                    style_header_node)

        content_z = zipfile.ZipFile(content_io, mode='a')
        content_z.writestr('content.xml',
                '<?xml version="1.0" encoding="UTF-8"?>' + \
                dom.documentElement.toxml('utf-8'))
        content_z.writestr('styles.xml',
                '<?xml version="1.0" encoding="UTF-8"?>' + \
                        dom_style.documentElement.toxml('utf-8'))

        if localcontext.get('pictures'):
            pictures.extend(localcontext['pictures'])
        for file, picture in pictures:
            content_z.writestr(file, picture)
        content_z.close()
        data = content_io.getvalue()
        content_io.close()
        output_format = report.output_format.format
        if output_format == 'pdf':
            data = self.convert_pdf(data)
        return (output_format, data)


    def convert_pdf(self, data):
        """
        Convert report to PDF using OpenOffice.org.
        This requires OpenOffice.org, pyuno and openoffice-python to
        be installed.
        """
        import tempfile
        try:
            import unohelper # installs import-hook
            import openoffice.interact
            import openoffice.officehelper as officehelper
            from openoffice.streams import OutputStream
            from com.sun.star.beans import PropertyValue
        except ImportError, exception:
            raise ExceptOSV('ImportError', str(exception))
        try:
            # connect to OOo
            desktop = openoffice.interact.Desktop()
        except officehelper.BootstrapException:
            raise ExceptOSV('Error', "Can't connect to (bootstrap) OpenOffice.org")

        res_data = None
        # Create temporary file (with name) and write data there.
        # We can not use NamedTemporaryFile here, since this would be
        # deleted as soon as we close it to allow OOo reading.
        #TODO use an input stream here
        fd_odt, odt_name = tempfile.mkstemp()
        fh_odt = os.fdopen(fd_odt, 'wb+')
        try:
            fh_odt.write(data)
            del data # save memory
            fh_odt.close()
            doc = desktop.openFile(odt_name, hidden=False)
            # Export as PDF
            buffer = StringIO.StringIO()
            out_props = (
                PropertyValue("FilterName", 0, "writer_pdf_Export", 0),
                PropertyValue("Overwrite", 0, True, 0),
                PropertyValue("OutputStream", 0, OutputStream(buffer), 0),
                )
            doc.storeToURL("private:stream", out_props)
            res_data = buffer.getvalue()
            del buffer
            doc.dispose()
        finally:
            fh_odt.close()
            os.remove(odt_name)
        if not res_data:
            ExceptOSV('Error', 'Error converting to PDF')
        return res_data

    def _parse_node(self, cursor, user, node, localcontext, context,
            node_context = None):
        if node_context is None:
            node_context = {}
        while True:
            if node.hasChildNodes():
                node = node.firstChild
            elif node.nextSibling:
                node = node.nextSibling
            else:
                while node and not node.nextSibling:
                    node = node.parentNode
                if not node:
                    break
                node = node.nextSibling
            if node in node_context:
                localcontext.update(node_context[node])
            if node.nodeType in (node.CDATA_SECTION_NODE, node.TEXT_NODE):
                res = self._parse_text(cursor, user, node, localcontext, context,
                        node_context)
                if isinstance(res, dom.Node):
                    node = res
            if node.nodeType == node.ELEMENT_NODE:
                if node.nodeName == "draw:frame":
                    self._parse_draw_frame(cursor, user, node, localcontext, context,)

    def _parse_draw_frame(self, cursor, user, node, localcontext, context):
        """When a picture name in the template document contain
        "replaceWith(content, extension)", this piture is replaced
        with the content, a file name is generated automatically with
        the given extension
        """
        if "replaceWith" not in node.attributes["draw:name"].nodeValue:
            return
        localcontext.setdefault('pictures', [])
        ctx = localcontext.copy()
        ctx.update(context)
        ctx["replaceWith"] = lambda x,y: (x,y)
        try:
            res = eval(node.attributes["draw:name"].nodeValue, ctx)
        except:
            Logger().notify_channel('report', LOG_ERROR,
                                    'Error on eval "%s"' % node.nodeValue)
            raise

        if isinstance(res, tuple) and  hasattr(res[0], 'getvalue'):
            data = res[0].getvalue()
            filename = 'Pictures/%s.%s'% (md5.new(data).hexdigest(), res[1])
            localcontext['pictures'].append((filename,data))
            for child_node in node.childNodes:
                if child_node.nodeName == "draw:image":
                    child_node.attributes["xlink:href"].nodeValue = filename
                    continue

    def _parse_text(self, cursor, user, node, localcontext, context,
            node_context):
        if node.parentNode.tagName == 'text:text-input':
            ctx = localcontext.copy()
            ctx.update(context)
            ctx['RepeatIn'] = lambda lst, name, parents=False: \
                    self.repeat_in(lst, name, parents=parents,
                            tnode=node, node_context=node_context)
            ctx['setTag'] = lambda oldtag, newtag, attrs=None: \
                    self.set_tag(oldtag, newtag, attrs=attrs, tnode=node)
            ctx['removeParentNode'] = lambda tag='p': \
                    self.remove_parent_node(tag, tnode=node)
            ctx['setLang'] = lambda lang: \
                    self.set_lang(lang, localcontext)
            ctx['formatLang'] = lambda value, digits=2, date=False: \
                    self.format_lang(value, digits=digits, date=date,
                            localcontext=localcontext)
            ctx['time'] = time
            ctx['datetime'] = datetime
            try:
                res = eval(node.nodeValue, ctx)
            except:
                Logger().notify_channel('report', LOG_ERROR,
                        'Error on eval "%s"' % node.nodeValue)
                raise
            if isinstance(res, bool):
                res = ''
            if hasattr(res, '__str__'):
                res = res.__str__()
            if isinstance(res, basestring):
                if '\n' in res:
                    parent2 = node.parentNode.parentNode
                    parent = node.parentNode
                    first = True
                    newnode = None
                    for val in res.decode('utf-8').split('\n'):
                        if first:
                            newnode = node
                            first = False
                        else:
                            newnode = node.cloneNode(1)
                        newnode.nodeValue = val
                        parent2.insertBefore(newnode, parent)
                        newnode = node.parentNode.cloneNode(1)
                        newnode.nodeType = newnode.ELEMENT_NODE
                        newnode.tagName = 'text:line-break'
                        newnode.firstChild.nodeValue = ''
                        if newnode.getAttribute('text:style-name'):
                            newnode.removeAttribute('text:style-name')
                        parent2.insertBefore(newnode, parent)
                    parent2.removeChild(parent)
                    if newnode:
                        parent2.removeChild(newnode)
                else:
                    node.nodeValue = res.decode('utf-8')
                    node.parentNode.parentNode.replaceChild(node, node.parentNode)
            return res
        if 'language' in localcontext:
            lang = localcontext['language']
            text = node.nodeValue
            if lang and text and not text.isspace():
                translation_obj = self.pool.get('ir.translation')
                new_text = translation_obj._get_source(cursor,
                        self._name, 'odt', lang, text)
                if new_text:
                    node.nodeValue = new_text.decode('utf-8')
        return None

    def repeat_in(self, lst, name, parents=False, tnode=None, node_context=None):
        node = self.find_parent(tnode, parents or PARENTS)

        pnode = node.parentNode
        nextnode = node.nextSibling
        pnode.removeChild(node)
        tnode.parentNode.parentNode.removeChild(tnode.parentNode)

        if not lst:
            return pnode
        for i in range(len(lst)):
            newnode = node.cloneNode(1)
            if nextnode:
                pnode.insertBefore(newnode, nextnode)
            else:
                pnode.appendChild(newnode)
            node_context[newnode] = {name: lst[i]}
        return pnode

    def set_tag(self, oldtag, newtag, attrs=None, tnode=None):
        if attrs is None:
            attrs = {}
        node = self.find_parent(tnode, [oldtag])
        if node:
            node.tagName = newtag
            for key, val in attrs.items():
                node.setAttribute(key, val)
        return None

    def remove_parent_node(self, tag='p', tnode=None):
        node = self.find_parent(tnode, [tag])
        if node:
            pnode = node.parentNode
            pnode.removeChild(node)
            return pnode

    def find_parent(self, node, parents):
        while True:
            if not node.parentNode:
                return None
            node = node.parentNode
            if node.nodeType == node.ELEMENT_NODE \
                    and node.localName in parents:
                break
        return node

    def find(self, tnode, tag):
        for node in tnode.childNodes:
            if node.nodeType == node.ELEMENT_NODE \
                    and node.localName == tag:
                return node
            res = self.find(node, tag)
            if res is not None:
                return res
        return None

    def set_lang(self, lang, localcontext):
        localcontext['language'] = lang
        _language_cache = localcontext['_language_cache']
        for obj in localcontext['objects']:
            obj._context['language'] = lang
            for table in obj._cache:
                for obj_id in obj._cache[table]:
                    _language_cache.setdefault(
                            obj._context['language'], {}).setdefault(
                                    table, {}).update(
                                            obj._cache[table][obj_id])
                    if lang in _language_cache \
                            and table in _language_cache[lang] \
                            and obj_id in _language_cache[lang][table]:
                        obj._cache[table][obj_id] = \
                                _language_cache[lang][table][obj_id]
                    else:
                        obj._cache[table][obj_id] = {'id': obj_id}
        return ''

    def format_lang(self, value, digits=2, date=False, localcontext=None):
        if localcontext is None:
            localcontext = {}
        encoding = locale.getdefaultlocale()[1]
        if encoding == 'utf':
            encoding = 'UTF-8'
        if encoding == 'cp1252':
            encoding = '1252'
        lang = localcontext.get('language', False) or 'en_US'
        try:
            if os.name == 'nt':
                lang = _LOCALE2WIN32.get(lang, lang)
            locale.setlocale(locale.LC_ALL, lang + '.' + encoding)
        except Exception:
            Logger().notify_channel('web-service', LOG_ERROR,
                    'Report %s: unable to set locale "%s"' % \
                            (self._name, lang + '.' + encoding))
        if date:
            if isinstance(value, time.struct_time):
                locale_format = LocaleTime().LC_date.replace('%y', '%Y')
                date = value
            else:
                # assume string, parse it
                if len(str(value)) == 10:
                    # length of date like 2001-01-01 is ten
                    # assume format '%Y-%m-%d'
                    locale_format = LocaleTime().LC_date.replace('%y', '%Y')
                    string_pattern = '%Y-%m-%d'
                else:
                    # assume format '%Y-%m-%d %H:%M:%S'
                    value = str(value)[:19]
                    locale_format = LocaleTime().LC_date.replace('%y', '%Y') \
                            + ' %H:%M:%S'
                    string_pattern = '%Y-%m-%d %H:%M:%S'
                date = time.strptime(str(value), string_pattern)
            return time.strftime(locale_format, date)

        return locale.format('%.' + str(digits) + 'f', value, True)
