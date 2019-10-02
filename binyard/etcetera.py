#!/usr/bin/env python
# things I don't know where to put
import sys
import builtins

def input(*args, **kwargs):
    if sys.version_info.major == 3:
        return builtins.input(*args, **kwargs)
    else:
        return raw_input(*args, **kwargs)

def input_until_correct(text, function, *args, **kwargs):
    while(True):
        answer = input(text)
        if function(answer, *args, **kwargs):
            return answer
