""" Contains general operations commonly used in manipulating calculation
    input or output files or any files really """

import os
import sys
import fnmatch
import re
import time
#pip
import scandir
import xml.etree.ElementTree as ET
import collections

#TODO: supposedly case insensitive
def listdirwith(path,file_list):
    """ Return list of directories under path containing file_list"""
    def files_are_there(filenames):
        #Check if ALL pattern in file_list exists in current dir's filenames
        #Unix-style regex is allowed
        for pattern in file_list:
            #print(pattern)
            #if not fnmatch.filter(filenames,pattern):
            #if not [n for n in filenames if fnmatch.fnmatch(n,pattern)]:
            if not [n for n in filenames if fnmatch.fnmatchcase(n,pattern)]:
                return False
        return True
    return [ dirpath
             for dirpath,dirnames,filenames in scandir.walk(path)\
             if files_are_there(filenames) and not 'rubbish' in dirpath ]
def find_file(path,pattern):
    """Wrapper for fnmatch.filter, with additional filecheck"""
    return [ os.path.join(path,filename) for filename in fnmatch.filter(os.listdir(path),pattern)\
             if os.path.isfile(os.path.join(path,filename)) ]
def readlineswith(filename,pattern='',do=lambda x:x,default=[]):
    """even more similar to grep+sed
       but return list instead of string"""
    try:
        out = open(filename,'r')
        regex_pattern = re.compile(pattern)
        e = [ do(line) for line in out.readlines() if regex_pattern.search(line) ]
        out.close()
        if not e: raise Exception('No matching line in '+filename)
        return e
    except IOError:
        err = sys.argv[0] + ': cannot access ' + filename + ': No such file'
        sys.exit(err)

#-----SAMPLE-----
#ned               : 128            #*! Number of down electrons (Integer)
#periodic          : T              #*! Periodic boundary conditions (Boolean)
#atom_basis_type   : blip           #*! Basis set type (Text)
#%block npcell
#4 4 1 
#%endblock npcell
def parse_casino(filename):
    casino_input = open(filename,'r')
    content = casino_input.read()
    casino_input.close()
    pattern_comment = re.compile(r'(?<=#).*$', re.MULTILINE)
    #key = re.compile(r'[a-zA-Z\_](?=\s*:)')
    #value = re.compile(r':')
    pattern_kv_pair = re.compile(r'(^.*)\:(.*$)', re.MULTILINE) #multiline input
    #pattern_key = re.compile(r'\w*(?=\s*:)') #so that ^ at every line
    pattern_key = re.compile(r'.*(?=:)') #so that ^ at every line
    pattern_value = re.compile(r'(?<=:).*?(?=#)')
    #block_key = re.compile(r'\%block\s*[a-zA-Z\_]\s*') #no multiline
    block = re.compile(r'(\%block\s*[a-zA-Z\_])(.*)(\%endblock[A-za-z\_\s]*)', re.MULTILINE|re.DOTALL) #multiline
    block_header = re.compile(r'(?<=\%block).*', re.MULTILINE)
    #parsed = collections.OrderedDict({'kv_pair':[],'block':[],'comment':[]}) #for kv -> '' : '', for block -> 'blockname': [lines]
    parsed = {'kv_pair':[],'block':[],'comment':[]} #for kv -> '' : '', for block -> 'blockname': [lines]
    #block_value = re.compile() #should be dynamically generated at loop
    #because we want to preserve order, look on line-by-line basis
    #final usage: dict[dtdmc] = 0.9
    #TODO: some confusing design decisions...
    for line in casino_input.readline():
        parsed['comment'] = (line,value)
        parsed['kv_pair'] = (line,key,value)
        parsed['block'] = (line,[])
    for comments in re.finditer(pattern_comment,content):
        print('-------COMMENT_LINES------')
        print(comments.group(0))
    for pairs in re.finditer(pattern_kv_pair,content):
        pair = pairs.group(0)
        key = re.search(pattern_key,pair).group(0).strip() if re.search(pattern_key,pair) else None
        value = re.search(pattern_value,pair).group(0).strip() if re.search(pattern_value,pair) else None
        parsed[key] = (key,value,line_number)
    for blocks in re.finditer(block,content):
        match = blocks.group(0)
        print('-------BLOCKS------')
        print(match)
        print('-------BLOCK_HEADERS------')
        for block_headers in re.finditer(block_header,match):
            match = block_headers.group(0)
            print(match)
    print parsed
#Copied from old parser.py lib
def parse_pbs(filename):
    pbs_file = open(filename,'r')
    #string_list = [
    #            v.split(' = ')
    #            for v in ''.join(pbs_file.readlines())
    #                .replace('\n\t','').replace('    ','')
    #                .split('\n')
    #                if ' = ' in v
    #         ]
    content = pbs_file.read()
    pbs_file.close()
    return fromstring_pbs(content)
def fromstring_pbs(string):
    string_list = [
            v.split(' = ')
            for v in string.replace('\n\t','').replace('    ','').split('\n') if ' = ' in v
            ]
    return dict(
             (key,value)
             for (key,value) in string_list
             )
#def parse_bash(filename):
def fromstring_bash(string,splitter=','):
    string_list = [
            v.split('=')
            for v in string.split(splitter)
            ]
    return dict(
             (key,value)
             for (key,value) in string_list
             )
#TODO:proper integration
def parse_upf(filename):
    upf_file = open(filename, 'r')
    content = upf_file.read()
    tags = re.compile(r'(?<=\<)([A-Za-z\_])+?(?=\>)') # <SOMETHING> pattern
    parsed = {}
    #data_array = []
    #re.match(data,content)
    for match in re.finditer(tags,content):
        tag = match.group(0)
        parsed[tag] = []
        regex = r'(?<=\<'+re.escape(tag)+r'\>)'+r'(.*?)(?=\<\/'+re.escape(tag)+'\>)'
        #print('REGEX: '+regex)
        block = re.compile(regex,re.DOTALL)
        parsed[tag] = [ line
                        for inner_match in re.finditer(block,content)
                        for line in inner_match.group(0).split('\n') if line ]
    #print parsed
    return parsed
    #for match in re.finditer(test,content):
    #    print(match.group(0)+'-------')
    #upf_file.close()
    #NOTE: not a true xml, so it does not work
#    tree = ET.parse(filename)
#    root = tree.getroot()
#    for child in root:
#        print child.tag, child.attrib
    #print root.ppinfo.tag
#TODO: make generic
def parse_pwx(filename):
    """Input: filename, Return: dictionary of pwx input tags and their values"""
    pwx_file = open(filename,'r')
    content = pwx_file.read()
    pwx_file.close()
    return fromstring_pwx(content)
def fromstring_pwx(string):
    #TODO:  change behaviour, namelist or card as attribute not group, keyword[type]=namelist/card
    """Return list of pw.x input parameters"""
    #string_list = [ line for line in string.split('\n') if line ]
    #parsed = { 'namelist': {},
    #           'card'    : {} }
    parsed = {}
    #Flags
    namelists = { 'control'  : None,
                       'system'   : None,
                       'electrons': None,
                       'ions'     : None,
                       'cell'     : None }
    cards = { 'atomic_species'  : None,
                   'atomic_positions': None,
                   'k_points'        : None,
                   'cell_parameters' : None,
                   'occupations'     : None,
                   'constraints'     : None,
                   'atomic_forces'   : None }
    end_namelist = re.compile('\s*/\s*')
    quoted = re.compile('\'.*\'')
    def set_namelist(key):
        for k in namelists.iterkeys():
            namelists[k] = True if k == key else False
    def set_card(key):
        for k in cards.iterkeys():
            cards[k] = True if k == key else False
    def get_namelistheader(line):
        for k in namelists.iterkeys():
            if '&'+k in line.lower():
                return k
        return False
    def get_cardheader(line):
        for k in cards.iterkeys():
            if k in re.sub(quoted,'',line.lower()):
                return k
        return False
    #not useful
    #def get_option(line):
    #    if '//' in re.sub('//','//',line):
    #        print line.split('//')[1]
    #        return line.split('//')[1] #Return part after //
    #        #To be eval'd
    for line in [ line for line in string.split('\n') if line ]:
        #Control lines
        #In namelist (see official pwscf documentation)
        #get_option(line)
        n = get_namelistheader(line)
        if n:
            set_namelist(n)
            set_card(None)
            #parsed['namelist'][n] = {}
            continue
        if re.match(end_namelist,line):
            set_namelist(None)
        #CARDS
        c = get_cardheader(line)
        if c:
            set_namelist(None)
            set_card(c)
            #parsed['card'][c] = {}
            #parsed['card'][c]['items'] = []
            #try:
                #parsed['card'][c]['options'] = re.search('{.*}',line).group(0).strip('{').strip('}')
                #parsed['card'][c]['options'] = re.split('\s*',line)[1].strip('{').strip('}')
            keyword = c
            for attempt in range(2):
                try:
                    OPT_COL = 1
                    parsed[keyword]['options'] = re.split(r'\s*',re.sub(r'\{|\}','',line))[OPT_COL].strip()
                except KeyError:
                    parsed[keyword] = {}
                    continue
                except IndexError:
                    try:
                        parsed[keyword]['options'] = ''
                    except KeyError:
                        parsed[keyword] = {}
                        parsed[keyword]['options'] = ''
                else:
                    break
            #except AttributeError:
            #    parsed['card'][c]['options'] = ''
            #except IndexError:
                #Error index due to no options
            #    parsed['card'][c]['options'] = ''
            continue
        #Process
        #TODO: switch based on in namelist or card
        for k,v in namelists.iteritems():
            if v:
                KEYWORD_COL = 0
                VALUE_COL = 1
                VALUE_VALUE_COL = 0
                VALUE_COMMENT_COL = 1
                #in input file: element[0] = element[1] !comment
                element = [ a.strip() for a in line.strip().split('=') ]
                #parsed['namelist'][k][element[0]] = element[1].split('!')[0].strip()
                keyword = element[KEYWORD_COL]
                for attempt in range(2):
                    try:
                        parsed[keyword]['value'] = element[VALUE_COL].split('!')[VALUE_VALUE_COL].strip()
                        parsed[keyword]['type'] = 'namelist'
                    except KeyError:
                        parsed[keyword] = {}
                        continue
                    else:
                        break
        for k,v in cards.iteritems():
            if v:
                #parsed['card'][k]['items'].append(re.split('\s+(?!$)',line.strip()))
                keyword = k
                for attempt in range(2):
                    try:
                        parsed[keyword]['value'].append(re.split(r'\s+',line.strip()))
                        parsed[keyword]['type'] = 'card'
                    except KeyError:
                        parsed[keyword]['value'] = []
                        continue
                    else:
                        break
    return parsed
def tostring_pwx(dictionary):
    """Return pw.x compatible string from pw.x input dictionary"""
    #Sorting orders
    #following standards defined at official documentation
    string = ""
    def namelist_order(key):
        order = { 'control'  : 1,
                  'system'   : 2,
                  'electrons': 3,
                  'ions'     : 4,
                  'cell'     : 5 }
        return order[key]
    def card_order(key):
        order = { 'atomic_species'  : 1,
                  'atomic_positions': 2,
                  'k_points'        : 3,
                  'cell_parameters' : 4,
                  'occupations'     : 5,
                  'constraints'     : 6,
                  'atomic_forces'   : 7 }
        return order[key]
    #for namelist_name in sorted(dictionary['namelist'].iterkeys(), key=namelist_order):
    namelists = [ d for d in dictionary if d['type'] == 'namelist' ]
    card      = [ d for d in dictionary if d['type'] == 'card' ]
    #for namelist_name in sorted(dictionary['namelist'].iterkeys(), key=namelist_order):
    for namelist_name in sorted(namelist[:].itervalues(), key=namelist_order):
        string += '&'+namelist_name+'\n'
        #namelist = dictionary['namelist'][namelist_name]
        for name,value in namelist.iteritems():
            string += ' '+name+'='+str(value)+'\n'
        string += '/'+'\n'
    #for card_name in sorted(dictionary['card'].iterkeys(), key=card_order):
    for card_name in sorted(card[:].itervalues(), key=card_order):
        card = dictionary['card'][card_name]
        string += card_name.upper()+' '+card['options']+'\n'
        for item in card['items']:
            string += ' '.join(item)+'\n'
    return string
def print_pwx(dictionary):
    """Write pw.x compatible input format based on that"""
    print(tostring_pwx(dictionary))
#def write_pwx(filename,dictionary):
#    out = open(filename, 'w')
#    out.print(tostring_pwx(dictionary))
#    out.close()
###DEPRECATED###
#def get_from_file(filename,*rules):
#    """ Return list of """
#    e = []
#    for rule in rules:
#        match = False
#        try:
#            grep = rule['condition']
#            sed = rule['task']
#            out = open(filename, 'r');
#            for line in out.readlines():
#                if grep(line):
#                    e.extend(sed(line))
#                    match = True
#            out.close()
#            if not match and rule['else']:
#                mark = rule['else']
#                e.extend(mark)
#        except IOError:
#            err = sys.argv[0] + ': ' + filename + ': No such file'
#            sys.exit(err)
#        except KeyError:
#            pass
#    if e:
#def get_dirs_with(file_set, root='./'):
#    """ Return generator of directories under root containing certain file_set"""
#    def files_are_there(filenames):
#        for pattern in file_set:
#            if not fnmatch.filter(filenames,pattern): #Allow regex in filename set
#                return False
#        return True
#    not_in_rubbish = lambda path: not 'rubbish' in path
#    return (dirpath for dirpath,dirnames,filenames in os.walk(root)\
#        if (files_are_there(filenames)) and not_in_rubbish(dirpath))
#        return e
#def get_from_file(filename,*rules):
#    """similar to grep+sed"""
#    e = []
#    for rule in rules:
#        try:
#            match = False
#            out = open(filename, 'r')
#            for line in out.readlines():
#                if rule.contain(line):
#                    e.extend(rule.do(line))
#                    match = True
#            out.close()
#            if not match:
#                e.extend(rule.default)
#        except IOError:
#            err = sys.argv[0] + ': cannot access ' + filename + ': No such file'
#            sys.exit(err)
#        except KeyError:
#            pass
#    return e
#
#def _line_contain(keyword):
#    """Return check function of some keyword in some line"""
#    return lambda line: keyword in line
#def line_contain(*keywords):
#    """Return chain of tests if line contain specified keywords"""
#    def contain_chain(line):
#        chain = True
#        for keyword in keywords:
#            chain = chain and _line_contain(keyword)(line)
#        return chain
#    return contain_chain
#def test_import():
#    print "OK"
#
#Classes
#class Rule:
#    """ Something """
#    def __init__(self, contain=None, do=None, default=None):
#        """ Create a new rule, with function contain, function do, and default list"""
#        #Return every line by default
#        self.contain = True if contain is None else contain
#        #Return whole line by default
#        if do is None:
#            self.do = lambda x: x
#        else:
#            self.do = do
#        #Empty default at no match
#        self.default = [] if default is None else default
#
