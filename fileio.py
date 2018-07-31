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
    for match in re.finditer(tags,content):
        tag = match.group(0)
        parsed[tag] = []
        regex = r'(?<=\<'+re.escape(tag)+r'\>)'+r'(.*?)(?=\<\/'+re.escape(tag)+'\>)'
        #print('REGEX: '+regex)
        block = re.compile(regex,re.DOTALL)
        parsed[tag] = [ line
                        for inner_match in re.finditer(block,content)
                        for line in inner_match.group(0).split('\n') if line ]
    return parsed
    #upf_file.close()
#TODO: make generic
def parse_pwx(filename):
    """Input: filename, Return: dictionary of pwx input tags and their values"""
    pwx_file = open(filename,'r')
    content = pwx_file.read()
    pwx_file.close()
    return fromstring_pwx(content)
def fromstring_pwx(string):
    """Return list of pw.x input parameters"""
    parsed = {}
    #Flags TODO: unified flag
    namelist_flag = { 'control'  : None,
                       'system'   : None,
                       'electrons': None,
                       'ions'     : None,
                       'cell'     : None }
    card_flag = { 'atomic_species'  : None,
                   'atomic_positions': None,
                   'k_points'        : None,
                   'cell_parameters' : None,
                   'occupations'     : None,
                   'constraints'     : None,
                   'atomic_forces'   : None }
    namelist_stop = re.compile('\s*/\s*')
    quoted = re.compile('\'.*\'')
    def set_namelist(key):
        for k in namelist_flag.iterkeys():
            namelist_flag[k] = True if k == key else False
    def set_card(key):
        for k in card_flag.iterkeys():
            card_flag[k] = True if k == key else False
    def get_namelist_start(line):
        for k in namelist_flag.iterkeys():
            if '&'+k in line.lower():
                return k
        return False
    def get_cardheader(line):
        for k in card_flag.iterkeys():
            if k in re.sub(quoted,'',line.lower()):
                return k
        return False
    # Split string on newlines
    for line in [ l for l in string.split('\n') if l ]:
        # Control lines
        namelist = get_namelist_start(line)
        card = get_cardheader(line)
        if namelist:
            # Set flag
            set_card(None)
            set_namelist(namelist)
            continue # Go to next line
        elif re.match(namelist_stop,line):
            set_namelist(None)
        elif card:
            set_namelist(None)
            set_card(card)
            parsed[card] = {} # Only allows one count of each card
            option_column = 1
            try:
                bare_line = re.sub(r'\{|\}', '', line)
                parsed[card]['options'] = re.split(r'\s*', bare_line)[option_column].strip()
            except IndexError:
                # no options, put empty string
                parsed[card]['options'] = ''
            continue # Go to next line
        # Read namelist/card contents
        # TODO: switch based on in namelist or card
        # Loop over all possible namelist (prevent including sporadic one)
        for namelist, flag in namelist_flag.iteritems():
            if flag:
                # format : name = value !comment
                # Remember that comment without whiteline is valid
                name_column = 0
                value_column = 1
                VALUE_VALUE_COL = 0
                VALUE_COMMENT_COL = 1
                line_element = [ a.strip() for a in line.strip().split('=') ]
                name = line_element[name_column]
                for attempt in range(2):
                    # Initialise name if not initialised
                    try:
                        parsed[name]['value'] = line_element[value_column].split('!')[VALUE_VALUE_COL].strip()
                        parsed[name]['type'] = 'name'
                        parsed[name]['namelist'] = namelist
                    except KeyError:
                        parsed[name] = {}
                        continue
                    else:
                        break
                break
        for card, flag in card_flag.iteritems():
            if flag:
                for attempt in range(2):
                    # Initialise value column if not initialised
                    try:
                        parsed[card]['value'].append(re.split(r'\s+',line.strip()))
                        parsed[card]['type'] = 'card'
                    except KeyError:
                        parsed[card]['value'] = []
                        continue
                    else:
                        break
                break
    return parsed


def tostring_pwx(dictionary):
    """Return pw.x compatible string from pw.x input dictionary"""
    # Initialise output string
    output_string = ""
    # Sorting orders, following standards specified in official documentation
    # Also, forget about non-typed invalid entries
    # key = names in namelists, card names
    # value = type, namelists, values
    def order(entry):
        key = entry[0]
        attribute = entry[1]
        order = { 'control'  : 1,
                  'system'   : 2,
                  'electrons': 3,
                  'ions'     : 4,
                  'cell'     : 5,
                  'atomic_species'  : 6,
                  'atomic_positions': 7,
                  'k_points'        : 8,
                  'cell_parameters' : 9,
                  'occupations'     : 10,
                  'constraints'     : 11,
                  'atomic_forces'   : 12 }
        if (attribute['type'] == 'name'):
            return order[attribute['namelist']]
        if (attribute['type'] == 'card'):
            return order[key]
        #print(key)
        return False

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
    #return dictionary.items()
    #return names
    # Write namelists first
    old_namelist = None
    for entry in sorted(dictionary.items(), key=order):
        # As splitted by .items() method
        key = entry[0]
        attribute = entry[1]
        # Writing rule depends on entry type. Skip type-less entries
        if attribute['type'] == 'name':
            namelist = attribute['namelist']
            if (namelist != old_namelist):
                if (old_namelist != None):
                    output_string += '/\n'
                old_namelist = namelist
                output_string += '&' + namelist + '\n'
            output_string += ' ' + key + '=' + str(attribute['value']) + '\n'
        if attribute['type'] == 'card':
            # Close namelist on namelists-cards transition
            if (old_namelist != None):
                old_namelist = None
                output_string += '/\n'
            card = key
            output_string += card.upper() + ' ' + attribute['options'] + '\n'
            for item in attribute['value']:
                output_string += ' '.join(map(str,item)) + '\n'
    return output_string

    #for namelist_name in sorted(dictionary['namelist'].iterkeys(), key=namelist_order):
    #    output_string += '&'+namelist_name+'\n'
    #    namelist = dictionary['namelist'][namelist_name]
    #    for name,value in namelist.iteritems():
    #        output_string += ' '+name+'='+str(value)+'\n'
    #    output_string += '/'+'\n'
    #for card_name in sorted(dictionary['card'].iterkeys(), key=card_order):
    #    card = dictionary['card'][card_name]
    #    output_string += card_name.upper()+' '+card['options']+'\n'
    #    for item in card['items']:
    #        output_string += ' '.join(item)+'\n'
    #return output_string


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
