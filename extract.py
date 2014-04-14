import xml.etree.cElementTree as ET
from collections import OrderedDict
import json
import re

class PebbleFunction(object):
    def __init__(self, node, kind):
        self.name = ''
        self.type = ''
        self.params = OrderedDict()
        self.description = ''
        self.ret_value = None
        self.warning = None
        self.kind = kind
        self.parse(node)

    def parse(self, node):
        """
        :type node: Element
        """
        self.type = self.unref(node.find('type'))
        self.name = self.unref(node.find('name'))
        for param in node.findall('param'):
            if param.find('declname') is not None:
                self.params[self.unref(param.find('declname'))] = {'name': self.unref(param.find('declname')), 'type': self.unref(param.find('type'))}

        # now dig in to the detailed information
        detail = node.find('detaileddescription')

        for l in (node.findall('.//itemizedlist') or []):
            l.text = '<ul>'
            l.getchildren()[-1].tail = '</ul>'
            for item in (l.findall('.//listitem') or []):
                item.text = (item.text or '') + '<li>'
                item.getchildren()[-1].tail = '</li>'

        for para in (node.findall('.//para') or []):
            para.text = '<p>' + (para.text or '')
            if len(para.getchildren()) > 0:
                para.getchildren()[-1].tail = (para.getchildren()[-1].tail or '') + '</p>'
            else:
                para.text += '</p>'

        if detail is not None:

            paramlists = detail.findall('.//parameterlist')
            for paramlist in paramlists:
                for param in paramlist.findall('parameteritem'):
                    name = param.find('parameternamelist/parametername').text
                    desc = param.find('parameterdescription/para')
                    if desc is not None:
                        desc = self.handle_desc(desc)
                    if name is not None and desc is not None and name in self.params:
                        self.params[name]['description'] = desc

                detail.find('.//parameterlist/..').remove(paramlist)

            ret_desc = detail.find(".//simplesect[@kind='return']")
            if ret_desc:
                self.ret_value = self.handle_desc(ret_desc)
                detail.find(".//simplesect[@kind='return']/..").remove(ret_desc)

            note = detail.find(".//simplesect[@kind='note']")
            if note:
                self.warning = self.handle_desc(note)
                detail.find(".//simplesect[@kind='note']/..").remove(note)

            see_also = detail.findall(".//simplesect[@kind='see']")
            for see in see_also:
                for child in see:
                    see.remove(child)


        self.description = self.handle_desc(detail) or self.handle_desc(node.find('briefdescription'))



    @classmethod
    def unref(cls, tag):
        if tag is None:
            return ''
        if len(tag.getchildren()) > 0:
            return cls.unref(tag.getchildren()[0])
        else:
            return tag.text

    @classmethod
    def handle_desc(cls, desc):
        if desc is None:
            return ''
        return re.sub(r'([a-zA-Z0-9]+_[a-zA-Z0-9_]+(?:\(\))?)', r'<code>\1</code>', ''.join(desc.itertext()).strip())

    def __str__(self):
        return "%s %s(%s)" % (self.type, self.name, ', '.join(['%s %s' % (self.params[x]['type'], self.params[x]['name']) for x in self.params]))

    def __repr__(self):
        return self.__str__()


def get_functions(root):
    return root.findall("compounddef/sectiondef[@kind='func']/memberdef")

def get_defines(root):
    return root.findall("compounddef/sectiondef[@kind='define']/memberdef")

def get_enums(root):
    return root.findall("compounddef/sectiondef[@kind='enum']/memberdef//enumvalue")

def get_typedefs(root):
    return root.findall("compounddef/sectiondef[@kind='typedef']/memberdef")

def do_something_useful():
    root = ET.XML(open("pebble__8h.xml").read())
    return [PebbleFunction(x, 'fn') for x in get_functions(root)] + \
           [PebbleFunction(x, 'def') for x in get_defines(root)] + \
           [PebbleFunction(x, 'enum') for x in get_enums(root)] + \
           [PebbleFunction(x, 'typedef') for x in get_typedefs(root)]

def to_json(stuff):
    result = {}
    for fn in stuff:
        result[fn.name] = {
            'returns': fn.type,
            'name': fn.name,
            'params': [{'name': fn.params[param]['name'], 'type': fn.params[param]['type'], 'description': fn.params[param].get('description', None)} for param in fn.params],
            'description': fn.description,
            'return_desc': fn.ret_value,
            'warning': fn.warning,
            'kind': fn.kind,
        }
    return json.dumps(result, indent=4)

def pretty_print():
    for fn in do_something_useful():
        print fn
        print "  %s" % fn.description
        if len(fn.params):
            print "  Params:"
            for param in fn.params:
                param = fn.params[param]
                print "    - %s %s: %s" % (param['type'], param['name'], param.get('description',''))
        print