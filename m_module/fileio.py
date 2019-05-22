""" Contains general operations commonly used in manipulating calculation
    input or output files or any files really """

import os
import sys
import fnmatch
import re
import time

#import scandir
import xml.etree.ElementTree as ET
import collections

# TODO: (BUG) supposedly case insensitive
def listdirwith(*filename_pattern_list, path='.'):
    """ Return list of directories that contain files in the list.
        May use wildcard matches (*) etc. as in shell.
        Input   : root path, list of searched filename patterns;
        Output  : --list-- of directories under path containing filename_pattern_list"""

    def files_are_there(filenames):
        """ Test whether ALL pattern in filename_pattern_list exists in current dir's filenames """
        #for pattern in filename_pattern_list:
            # If no files in the directory match specified pattern, return false
        for pattern in filename_pattern_list:
            if not [ n for n in filenames if fnmatch.fnmatchcase(n, pattern) ]:
                return False
        return True

    return [ dirpath
        #for dirpath,dirnames,filenames in scandir.walk(path)
        for dirpath,dirnames,filenames in os.walk(path)
        if files_are_there(filenames)
        and not 'rubbish' in dirpath ]


def find_file(path, pattern):
    """Wrapper for fnmatch.filter, with additional filecheck"""
    return [ os.path.join(path,filename) for filename in fnmatch.filter(os.listdir(path),pattern)
             if os.path.isfile(os.path.join(path,filename)) ]


# TODO: make this more generic by:
# @regex for preincluded pattern, normally only accepts function
# @from_file when want to use filename as filehandle
# NOTE: does not really match decorator pattern...
#def from_file(function):
#    def filehandled(filename, *args, **kwargs):
#        with open(filename, 'r') as the_file:
#            function(the_file, *args, **kwargs)
#    return filehandled

def readlineswith(filehandle, *pattern_list, after=0, process=lambda x:x, default=[], count=False):
    """ Return list of lines that match specified pattern(s) (OR match)
        with optional extra action """
    if count:
        count = 0
        for line in filehandle.readlines():
            for pattern in pattern_list:
                if re.search(pattern, line):
                    count += 1
        return count
    else:
        e = []
        echo = 0
        for line in filehandle.readlines():
            for pattern in pattern_list:
                if re.search(pattern, line):
                    # TODO: still not decided whether it is better to include None
                    processed_line = process(line)
                    if processed_line:
                        e.append(processed_line)
                    echo = after
                elif echo:
                    processed_line = process(line)
                    if processed_line:
                        e.append(processed_line)
                    echo -= 1
        if e:
            return e

def split_count(indexed):
    try:
        tag, count = re.split(r'\[|\]', indexed)[:-1] #discard last element
        count = int(count)
    except ValueError:
        tag = indexed
        count = None
    return (tag, count)

# Useful for getting elements from qmcpack's xml (but I'm no longer sure how)
# always return a list except when "tree" is an attrib
# TODO: should return a list of matching objects
# sample objString: name.name.name
def get_xmlelement_from_obj(element, objString):
    """ Return the value (in a list) of a unique xml element or attribute
        from a tree with the specified objString, raise exception otherwise """
    objtags = objString.split('.')
    next_objString = '.'.join(objtags[1:])
    #if not element:
    #    print(element)
    #    return element

    tag, count = split_count(objtags[0])
    child_elements = element.findall(tag)
    if count is None:
        if len(child_elements) > 1:
            sys.exit('There are {} elements with \'{}\' tag'.format(len(child_elements), tag))
        if child_elements:
            child_element = child_elements[0]
        else:
            try:
                return element.attrib[tag]
            except KeyError:
               sys.exit('No attribute or elements under {} with the name of {}'.format(element, tag))
    else:
        child_element = child_elements[count]
    if not child_element is None:
        if next_objString:
            return get_xmlelement_from_obj(child_element, next_objString)
        else:
            return child_element
    else: # no child with tag; possibly reffering to an attribute
        try:
            return element.attrib[tag]
        except KeyError:
           sys.exit('No attribute or elements under {} with the name of {}'.format(element, tag))


def parse_casino(filename):
    """ Input: casino input filepath, Output: Dictionary of casino keywords values """
    # Input format snippet :
    #ned               : 128            #*! Number of down electrons (Integer)
    #periodic          : T              #*! Periodic boundary conditions (Boolean)
    #atom_basis_type   : blip           #*! Basis set type (Text)
    #%block npcell
    #4 4 1
    #%endblock npcell
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
    print(parsed)


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


def parse_pwx2(open_file):
    """Input: pw.x input filehandle Output: dictionary of pw.x input tags"""
    #TODO: make this default parse_pwx
    return fromstring_pwx(open_file.read())


#TODO: recognize comman (,) separated input as newline
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
        for k in namelist_flag.keys():
            namelist_flag[k] = True if k == key else False

    def set_card(key):
        for k in card_flag.keys():
            card_flag[k] = True if k == key else False

    def get_namelist_start(line):
        for k in namelist_flag.keys():
            if '&'+k in line.lower():
                return k
        return False

    def get_cardheader(line):
        for k in card_flag.keys():
            if k in re.sub(quoted,'',line.lower()):
                return k
        return False


    # Split string on newlines and comma
    for i, line in enumerate(( l for l in re.split(r'[\n,]', string) if l )):
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
                line_stripped = re.sub(r'(\{|\}|\(|\)|\=)', ' ', line)
                alphabet_character = re.compile(r'[A-za-z]')
                option = re.compile(r'(?<!^)(?<=\s)[A-za-z]+(?=\s*)')
                parsed[card]['options'] = option.search(line_stripped).group(0)
            except AttributeError:
                # no options, put empty string
                parsed[card]['options'] = ''
            continue # Go to next line
        # Read namelist/card contents
        # TODO: switch based on in namelist or card
        # Loop over all possible namelist (prevent including sporadic one)
        for namelist, flag in namelist_flag.items():
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
                        parsed[name]['sort'] = i
                    except KeyError:
                        parsed[name] = {}
                        continue
                    else:
                        break
                break
        for card, flag in card_flag.items():
            if flag:
                for attempt in range(2): # try again once if fails
                    # Initialise value column if not initialised
                    try:
                        parsed[card]['value'].append(re.split(r'\s+',line.strip()))
                        parsed[card]['type'] = 'card'
                        parsed[card]['sort'] = i
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

    def namesort(entry):
        key = entry[0]
        attribute = entry[1]
        if (attribute['type'] == 'card'):
            return False
        if (attribute['type'] == 'name'):
            return attribute['sort']
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
    for entry in sorted(sorted(dictionary.items(), key=namesort), key=order):
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
            # Note that each item == one line of card
            for item in attribute['value']:
                # Treat numerical details differently
                if card == 'cell_parameters':
                    #try:
                    formatted = [ "{:0.15f}".format(float(x)) for x in item ]
                    #except ValueError:
                        # sometimes positions are still left in original string
                        #formatted = [ "{:0.15f}".format(float(x)) for x in item ]
                    output_string += ' '.join(formatted) + '\n'
                elif card == 'atomic_positions':
                    # remember that the first element is atom type
                    #formatted = [ "{:0.15f}".format(float(x)) else "{:3}".format(x)
                    def pos_format(i,x):
                        if i == 0:
                            return "{:3}".format(x)
                        if i <= 3:
                            return "{:0.15f}".format(float(x))
                        else:
                            return "{:d}".format(int(x))
                    formatted = [ pos_format(i,x)
                                  for i,x in enumerate(item) ]
                    output_string += ' '.join(formatted) + '\n'
                else:
                    #print(item)
                    try:
                        output_string += ' '.join(map(str,item)) + '\n'
                    except TypeError:
                        # if only one element in a line (not a list)
                        output_string += str(item) + '\n'
    return output_string
